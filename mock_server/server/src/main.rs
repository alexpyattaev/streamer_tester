//! This example demonstrates quic server for handling incoming transactions.
//!
//! Checkout the `README.md` for guidance.
use shared::stats_collection::{file_bin, StatsCollection, StatsSample};
use std::io::Write;
use std::sync::mpsc::{channel, Receiver, Sender};
use {
    chrono::Utc,
    pem::Pem,
    server::{
        cli::{build_cli_parameters, ServerCliParameters},
        format_as_bits::format_as_bits,
        packet_accumulator::{PacketAccumulator, PacketChunk},
        // This is the new certificate used in v2
        tls_certificates::new_dummy_x509_certificate,
        QuicServerError,
        SkipClientVerification,
        QUIC_MAX_TIMEOUT,
    },
    smallvec::SmallVec,
    solana_sdk::{
        packet::{Meta, PACKET_DATA_SIZE},
        signature::Keypair,
    },
    solana_streamer::nonblocking::quic::ALPN_TPU_PROTOCOL_ID,
    std::{
        net::SocketAddr,
        sync::{
            atomic::{AtomicU64, Ordering},
            Arc,
        },
        time::Instant,
    },
    tokio::{
        fs::File,
        io::{AsyncWriteExt, BufWriter},
        signal,
        sync::mpsc::{unbounded_channel, UnboundedReceiver, UnboundedSender},
        time::{self, Duration},
    },
    tokio_util::sync::CancellationToken,
    tracing::{debug, error, info, info_span, trace, warn},
};
use {
    quinn::{Chunk, Connection, ConnectionError, Endpoint, IdleTimeout, ServerConfig},
    quinn_proto::crypto::rustls::QuicServerConfig,
};

/// Returns default server configuration along with its PEM certificate chain.
#[allow(clippy::field_reassign_with_default)] // https://github.com/rust-lang/rust-clippy/issues/6527
fn configure_server(
    identity_keypair: &Keypair,
    max_concurrent_streams: u32,
    stream_receive_window_size: u32,
    receive_window_size: u32,
) -> Result<(ServerConfig, String), QuicServerError> {
    let (cert, priv_key) = new_dummy_x509_certificate(identity_keypair);
    let cert_chain_pem_parts = vec![Pem {
        tag: "CERTIFICATE".to_string(),
        contents: cert.as_ref().to_vec(),
    }];
    let cert_chain_pem = pem::encode_many(&cert_chain_pem_parts);

    let mut server_tls_config = rustls::ServerConfig::builder()
        .with_client_cert_verifier(SkipClientVerification::new())
        .with_single_cert(vec![cert], priv_key)?;
    server_tls_config.alpn_protocols = vec![ALPN_TPU_PROTOCOL_ID.to_vec()];
    let quic_server_config = QuicServerConfig::try_from(server_tls_config)?;

    let mut server_config = ServerConfig::with_crypto(Arc::new(quic_server_config));
    let config = Arc::get_mut(&mut server_config.transport).unwrap();

    // Originally, in agave it is set to 256 (see below) but later depending on the stake it is
    // reset to value up to QUIC_MAX_STAKED_CONCURRENT_STREAMS (512)
    // QUIC_MAX_CONCURRENT_STREAMS doubled, which was found to improve reliability
    //const MAX_CONCURRENT_UNI_STREAMS: u32 =
    //    (QUIC_MAX_UNSTAKED_CONCURRENT_STREAMS.saturating_mul(2)) as u32;
    config.max_concurrent_uni_streams(max_concurrent_streams.into());
    config.stream_receive_window(stream_receive_window_size.into());
    // was: config.receive_window((PACKET_DATA_SIZE as u32).into());
    config.receive_window(receive_window_size.into());
    let timeout = IdleTimeout::try_from(QUIC_MAX_TIMEOUT).unwrap();
    config.max_idle_timeout(Some(timeout));

    // disable bidi & datagrams
    const MAX_CONCURRENT_BIDI_STREAMS: u32 = 0;
    config.max_concurrent_bidi_streams(MAX_CONCURRENT_BIDI_STREAMS.into());
    config.datagram_receive_buffer_size(None);

    // Disable GSO. The server only accepts inbound unidirectional streams initiated by clients,
    // which means that reply data never exceeds one MTU. By disabling GSO, we make
    // quinn_proto::Connection::poll_transmit allocate only 1 MTU vs 10 * MTU for _each_ transmit.
    // See https://github.com/anza-xyz/agave/pull/1647.
    config.enable_segmentation_offload(false);

    Ok((server_config, cert_chain_pem))
}

/// Constructs a QUIC endpoint configured to listen for incoming connections on a certain address
/// and port.
///
/// ## Returns
///
/// - a stream of incoming QUIC connections
/// - server certificate serialized into DER format
fn create_server_endpoint(
    bind_addr: SocketAddr,
    server_config: ServerConfig,
) -> Result<Endpoint, QuicServerError> {
    //TODO(klykov): this is done in spawn_server in streamer/src/nonblocking/quic.rs
    // we use new instead of server for no reason there
    Ok(Endpoint::server(server_config, bind_addr)?)
}

fn main() {
    // Check if output is going to a terminal (stdout)
    let is_terminal = atty::is(atty::Stream::Stderr);
    tracing::subscriber::set_global_default(
        tracing_subscriber::FmtSubscriber::builder()
            .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
            .with_writer(std::io::stderr)
            .with_ansi(is_terminal)
            .finish(),
    )
    .unwrap();
    let parameters = build_cli_parameters();
    let code = {
        if let Err(e) = run(parameters) {
            eprintln!("ERROR: {e}");
            1
        } else {
            0
        }
    };
    ::std::process::exit(code);
}

#[derive(Debug, Default)]
struct Stats {
    num_received_streams: AtomicU64,
    num_errored_streams: AtomicU64,
    num_accepted_connections: AtomicU64,
    num_refused_connections: AtomicU64,
    num_connection_errors: AtomicU64,
    num_finished_streams: AtomicU64,
    num_received_bytes: AtomicU64,
}

impl Stats {
    /// Load the current state into a new Stats object
    fn load_current(&self) -> Stats {
        Stats {
            num_received_streams: AtomicU64::new(self.num_received_streams.load(Ordering::Relaxed)),
            num_errored_streams: AtomicU64::new(self.num_errored_streams.load(Ordering::Relaxed)),
            num_accepted_connections: AtomicU64::new(
                self.num_accepted_connections.load(Ordering::Relaxed),
            ),
            num_refused_connections: AtomicU64::new(
                self.num_refused_connections.load(Ordering::Relaxed),
            ),
            num_connection_errors: AtomicU64::new(
                self.num_connection_errors.load(Ordering::Relaxed),
            ),
            num_finished_streams: AtomicU64::new(self.num_finished_streams.load(Ordering::Relaxed)),
            num_received_bytes: AtomicU64::new(self.num_received_bytes.load(Ordering::Relaxed)),
        }
    }

    /// Calculate and log the differences between two `Stats` instances
    fn log_tps_bitrate(&self, previous: &Stats) {
        let diff_finished_streams = self.num_finished_streams.load(Ordering::Relaxed)
            - previous.num_finished_streams.load(Ordering::Relaxed);
        let diff_received_bytes = self.num_received_bytes.load(Ordering::Relaxed)
            - previous.num_received_bytes.load(Ordering::Relaxed);

        info!(
            "tps: {}, bitrate: {}",
            diff_finished_streams,
            format_as_bits(diff_received_bytes as f64)
        );
    }
}

#[tokio::main]
async fn run(options: ServerCliParameters) -> Result<(), QuicServerError> {
    let (sender, receiver) = channel::<u32>();
    std::thread::spawn(move || {
        let mut file = file_bin("Server".into()).unwrap();

        while let Ok(timestamp) = receiver.recv() {
            file.write_all(&timestamp.to_ne_bytes()).unwrap();
        }
    });

    let token = CancellationToken::new();
    let stats = Arc::new(Stats::default());
    // Spawn a task that listens for SIGINT (Ctrl+C)
    let handler = tokio::spawn({
        let token = token.clone();
        async move {
            if signal::ctrl_c().await.is_ok() {
                println!("Received Ctrl+C, shutting down...");
                token.cancel();
            }
        }
    });

    let ServerCliParameters {
        stateless_retry,
        listen,
        connection_limit,
        max_concurrent_streams,
        stream_receive_window_size,
        receive_window_size,
        reordering_log_file,
        log,
    } = options;

    let identity = Keypair::new();
    let (server_config, _) = configure_server(
        &identity,
        max_concurrent_streams,
        stream_receive_window_size,
        receive_window_size,
    )?;
    let endpoint = create_server_endpoint(listen, server_config)?;
    info!("listening on {}", endpoint.local_addr()?);

    run_report_stats_service(stats.clone(), token.clone()).await;
    let start: Instant = Instant::now();
    loop {
        tokio::select! {
            _ = token.cancelled() => {
                println!("{stats:?}");
                break;
            }
            conn = endpoint.accept() => {
                let Some(conn) = conn else {
                    continue;
                };
                if check_connection_limit(&endpoint, connection_limit)
                {
                    warn!("refusing due to open connection limit");
                    stats
                        .num_refused_connections
                        .fetch_add(1, Ordering::Relaxed);

                    conn.refuse();
                } else if stateless_retry && !conn.remote_address_validated() {
                    warn!("requiring connection to validate its address");
                    conn.retry().unwrap();
                } else {
                    info!("accepting connection");
                    stats
                        .num_accepted_connections
                        .fetch_add(1, Ordering::Relaxed);
                    let connection = conn.await?;
                    let fut = handle_connection(connection, reordering_log_file.clone(), stats.clone(), token.clone(), sender.clone(), start.clone());
                    tokio::spawn(async move {
                        if let Err(e) = fut.await {
                            error!("connection failed: {reason}", reason = e.to_string())
                        }
                    });
                }
            }
        }
    }

    let _ = handler.await;

    Ok(())
}

fn check_connection_limit(endpoint: &Endpoint, connection_limit: Option<usize>) -> bool {
    connection_limit.map_or(false, |n| endpoint.open_connections() >= n)
}

struct TxInfo {
    pub tx_id: usize,
    pub timestamp_ms: u64,
}

impl From<&[u8]> for TxInfo {
    fn from(data: &[u8]) -> Self {
        assert!(data.len() >= 16);
        let tx_id = usize::from_le_bytes(data[0..8].try_into().unwrap());
        let timestamp_ms = u64::from_le_bytes(data[8..16].try_into().unwrap());

        TxInfo {
            tx_id,
            timestamp_ms,
        }
    }
}

async fn handle_connection(
    connection: Connection,
    reordering_log_file: Option<String>,
    stats: Arc<Stats>,
    token: CancellationToken,
    thread_sender: Sender<u32>,
    start: Instant,
) -> Result<(), QuicServerError> {
    async {
        let span = info_span!(
            "connection",
            remote = %connection.remote_address(),
        );
        let _enter = span.enter();
        info!("Connection have been established.");

        let tx_info_sender = if let Some(reordering_log_file) = reordering_log_file {
            let (tx_info_sender, tx_info_receiver) = unbounded_channel::<TxInfo>();
            let connection_id = connection.stable_id();
            run_reorder_log_service(
                format!("{reordering_log_file}-{connection_id}.csv"),
                tx_info_receiver,
            )
            .await;
            Some(tx_info_sender)
        } else {
            None
        };

        // Each stream initiated by the client constitutes a new request.
        loop {
            if token.is_cancelled() {
                info!("Stop handling connection...");
                return Ok(());
            }
            let stream = connection.accept_uni().await;
            let mut stream = match stream {
                Err(ConnectionError::ApplicationClosed { .. }) => {
                    info!("connection closed");
                    return Ok(());
                }
                Err(e) => {
                    stats.num_connection_errors.fetch_add(1, Ordering::Relaxed);
                    return Err(e);
                }
                Ok(s) => s,
            };
            // do the same as in the agave
            let mut packet_accum: Option<PacketAccumulator> = None;
            let stats = stats.clone();
            // In agave we spawn for each stream, yet it is better not
            //tokio::spawn({
            //let tx_info_sender = tx_info_sender.clone();
            //async move {
            loop {
                let Ok(chunk) = stream.read_chunk(PACKET_DATA_SIZE, true).await else {
                    debug!("Stream failed");
                    stats.num_errored_streams.fetch_add(1, Ordering::Relaxed);
                    break; // not sure if the right thing to do
                };
                let res = handle_stream_chunk_accumulation(
                    chunk,
                    &mut packet_accum,
                    &tx_info_sender,
                    &stats,
                )
                .await;
                if let Err(e) = res {
                    error!("failed: {reason}", reason = e.to_string());
                    stats.num_errored_streams.fetch_add(1, Ordering::Relaxed);
                    break;
                }
                if res.unwrap() {
                    trace!("Finished stream.");

                    stats.num_finished_streams.fetch_add(1, Ordering::Relaxed);
                    break;
                }

                stats.num_received_streams.fetch_add(1, Ordering::Relaxed);
                let dt = start.elapsed().as_micros() as u32;
                let _ = thread_sender.send(dt);
            }
            //}
            //});
        }
    }
    .await?;
    Ok(())
}

// returns if stream was closed
async fn handle_stream_chunk_accumulation(
    chunk: Option<Chunk>,
    packet_accum: &mut Option<PacketAccumulator>,
    tx_info_sender: &Option<UnboundedSender<TxInfo>>,
    stats: &Arc<Stats>,
) -> Result<bool, QuicServerError> {
    let Some(chunk) = chunk else {
        //it means that the last chunk has been received, we put all the chunks
        //accumulated to some channel
        if let Some(accum) = packet_accum.take() {
            handle_packet_bytes(accum, tx_info_sender, &stats).await;
        }
        return Ok(true);
    };
    let chunk_len = chunk.bytes.len() as u64;
    debug!("got chunk of len: {chunk_len}");
    // This code is copied from nonblocking/quic.rs. Interesting to know if
    // these checks are sufficient. shouldn't happen, but sanity check the size
    // and offsets
    if chunk.offset > PACKET_DATA_SIZE as u64 || chunk_len > PACKET_DATA_SIZE as u64 {
        debug!("failed validation with chunk_len={chunk_len} > {PACKET_DATA_SIZE}");
        return Err(QuicServerError::FailedReadChunk);
    }
    let Some(end_of_chunk) = chunk.offset.checked_add(chunk_len) else {
        debug!("failed validation on offset overflow");
        return Err(QuicServerError::FailedReadChunk);
    };
    if end_of_chunk > PACKET_DATA_SIZE as u64 {
        debug!("failed validation on end_of_chunk={end_of_chunk} > {PACKET_DATA_SIZE}");
        return Err(QuicServerError::FailedReadChunk);
    }

    // chunk looks valid
    // accumulate chunks into packet but what's the reason
    // if we stick with tx to be limited by PACKET_DATA_SIZE
    if packet_accum.is_none() {
        let meta = Meta::default();
        //meta.set_socket_addr(remote_addr); don't care much in the context of this app
        *packet_accum = Some(PacketAccumulator {
            meta,
            chunks: SmallVec::new(),
            start_time: Instant::now(),
        });
    }
    if let Some(accum) = packet_accum.as_mut() {
        let offset = chunk.offset;
        let Some(end_of_chunk) = (chunk.offset as usize).checked_add(chunk.bytes.len()) else {
            debug!("failed validation on offset overflow when accumulating chunks");
            return Err(QuicServerError::FailedReadChunk);
        };
        accum.chunks.push(PacketChunk {
            bytes: chunk.bytes,
            offset: offset as usize,
            end_of_chunk,
        });

        accum.meta.size = std::cmp::max(accum.meta.size, end_of_chunk);
    }
    Ok(false)
}

async fn handle_packet_bytes(
    accum: PacketAccumulator,
    tx_info_sender: &Option<UnboundedSender<TxInfo>>,
    stats: &Arc<Stats>,
) {
    debug!(
        "Num chunks {}, Received data size {}",
        accum.chunks.len(),
        accum.meta.size
    );
    if let Some(tx_info_sender) = tx_info_sender {
        // probably, it is possible to use one buffer for all of the streams,
        // for code simplicity don't do it here.
        let mut dest: [u8; 1232] = [0; 1232];
        for chunk in &accum.chunks {
            dest[chunk.offset..chunk.end_of_chunk].copy_from_slice(&chunk.bytes);
        }

        let tx_info = TxInfo::from(&dest[0..16]);

        tx_info_sender
            .send(tx_info)
            .expect("Receiver should not be dropped.");
    }

    stats
        .num_received_bytes
        .fetch_add((accum.meta.size) as u64, Ordering::Relaxed);
}

async fn run_reorder_log_service(
    file_name: String,
    mut tx_info_receiver: UnboundedReceiver<TxInfo>,
) {
    let file = File::create(file_name)
        .await
        .expect("We should be able to create a file for log");
    // it will flush when the buffer is full, so each 64KB because it is typical sector size.
    let mut writer = BufWriter::with_capacity(64 * 1024, file);
    let line = format!(
        "timestamp,max_seen_tx_id,timestamp_max_seen_ms,current_tx_id,timestamp_current_ms\n"
    );
    writer.write_all(line.as_bytes()).await.unwrap();

    let _ = tokio::spawn(async move {
        let mut max_seen_tx_info: Option<TxInfo> = None;
        loop {
            let Some(tx_info) = tx_info_receiver.recv().await else {
                info!("Stop tx_info processing task...");
                break;
            };
            match max_seen_tx_info {
                None => {
                    max_seen_tx_info = Some(tx_info);
                }
                Some(ref mut max_seen) => {
                    let now = Utc::now();
                    let line = format!(
                        "{now},{},{},{},{}\n",
                        max_seen.tx_id, max_seen.timestamp_ms, tx_info.tx_id, tx_info.timestamp_ms
                    );
                    writer.write_all(line.as_bytes()).await.unwrap();

                    // Update max_seen_tx_info if the new tx_id is greater
                    if tx_info.tx_id > max_seen.tx_id {
                        *max_seen = tx_info;
                    }
                }
            }
        }
        writer.flush().await.unwrap();
    });
}

async fn run_report_stats_service(stats: Arc<Stats>, token: CancellationToken) {
    tokio::spawn({
        async move {
            let mut previous_stats = Stats::default();
            let mut interval = time::interval(Duration::from_secs(1));
            loop {
                tokio::select! {
                _ = token.cancelled() => {
                    println!("{stats:?}");
                    break;
                }
                _ = interval.tick() => {
                        stats.log_tps_bitrate(&previous_stats);
                        previous_stats = stats.load_current();
                    }
                }
            }
        }
    });
}
