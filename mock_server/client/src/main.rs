#![allow(clippy::arithmetic_side_effects)]
//! This example demonstrates an HTTP client that requests files from a server.
//!
//! Checkout the `README.md` for guidance.

use chrono::{NaiveDate, NaiveDateTime, NaiveTime, Utc};
/*use bytemuck::{AnyBitPattern, NoUninit};
use client::quic_networking::ConnectionState;
use tracing::debug;
use std::sync::atomic::Ordering::Relaxed;*/
use quinn::ClientConfig;
use shared::stats_collection::{file_bin, StatsSample};
use solana_sdk::{pubkey::Pubkey, signer::Signer};
use std::io::Write as _;
use tracing::error;
use {
    client::{
        cli::{build_cli_parameters, ClientCliParameters},
        error::QuicClientError,
        quic_networking::{
            create_client_config, create_client_endpoint, send_data_over_stream,
            QuicClientCertificate,
        },
        transaction_generator::generate_dummy_data,
    },
    solana_sdk::{packet::PACKET_DATA_SIZE, signature::Keypair, signer::EncodableKey},
    std::{
        sync::Arc,
        time::{Duration, Instant, SystemTime, UNIX_EPOCH},
    },
    tokio::time::sleep,
    tracing::info,
};

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
    let opt = build_cli_parameters();
    let code = {
        if let Err(e) = run(opt) {
            println!("ERROR: {e}");
            1
        } else {
            0
        }
    };
    ::std::process::exit(code);
}

#[tokio::main(flavor = "multi_thread", worker_threads = 8)]
async fn run(parameters: ClientCliParameters) -> anyhow::Result<()> {
    let identity = if let Some(staked_identity_file) = parameters.staked_identity_file.clone() {
        Keypair::read_from_file(staked_identity_file)
            .map_err(|_err| QuicClientError::KeypairReadFailure)?
    } else {
        Keypair::new()
    };
    let client_certificate = Arc::new(QuicClientCertificate::new(&identity));

    let mut join_set = tokio::task::JoinSet::new();

    for id in 0..parameters.num_connections as u64 {
        let client_config =
            create_client_config(client_certificate.clone(), parameters.disable_congestion);
        join_set.spawn(run_endpoint(
            client_config,
            parameters.clone(),
            identity.pubkey(),
            id,
        ));
    }
    let mut total_sent: Vec<StatsSample> = Vec::with_capacity(10 * 1024 * 1024);
    for result in join_set.join_all().await {
        let mut result = match result {
            Ok(result) => result,
            Err(e) => {
                eprintln!("{e}");
                continue;
            }
        };
        total_sent.append(&mut result);
    }
    total_sent.sort_by(|a, b| a.time_stamp.cmp(&b.time_stamp));
    if let Some(host_name) = parameters.host_name.clone() {
        let mut writer = file_bin(host_name.clone())?;
        for val in &total_sent {
            writer.write_all(bytemuck::bytes_of(val)).unwrap();
        }
        writer.flush().unwrap();
        let total_sent = total_sent.len() as u64;
        info!("TRANSACTIONS_SENT {}", total_sent);
        let mut num_sent_file =
            std::fs::File::create(format!("results/{}.summary", host_name)).unwrap();
        num_sent_file.write_all(&total_sent.to_ne_bytes()).unwrap();
    }

    println!("Successfully completed!");
    Ok(())
}

// quinn has one global per-endpoint lock, so multiple endpoints help get around that
async fn run_endpoint(
    client_config: ClientConfig,
    ClientCliParameters {
        target,
        bind,
        duration,
        tx_size,
        max_txs_num,
        num_connections,
        ..
    }: ClientCliParameters,
    identity: Pubkey,
    connection_id: u64,
) -> Result<Vec<StatsSample>, QuicClientError> {
    let endpoint =
        create_client_endpoint(bind, client_config).expect("Endpoint creation should not fail.");

    let connection = endpoint.connect(target, "connect")?.await?;

    // avoid allocations for up to 10M samples
    let mut stats_collector: Vec<StatsSample> = Vec::with_capacity(10 * 1024 * 1024);

    let start = Instant::now();
    let solana_epoch = NaiveDateTime::new(
        NaiveDate::from_ymd_opt(2020, 3, 16).unwrap(),
        NaiveTime::MIN,
    );
    let mut transaction_id = 0;
    let mut tx_buffer = [0u8; PACKET_DATA_SIZE];
    let max_bitrate_bps = 200e6;
    let time_between_txs = (tx_size * 8) as f64 / max_bitrate_bps;

    loop {
        let con_stats = connection.stats();
        let now = Utc::now().naive_utc();
        let delta_time = (now - solana_epoch).num_microseconds().unwrap() as u64;
        let stats = StatsSample {
            udp_tx: con_stats.udp_tx.bytes,
            udp_rx: con_stats.udp_rx.bytes,
            time_stamp: delta_time,
            congestion_events: con_stats.path.congestion_events,
            congestion_window: con_stats.path.cwnd,
            lost_packets: con_stats.path.lost_packets,
            connection_id,
        };
        stats_collector.push(stats);

        if let Some(duration) = duration {
            if start.elapsed() >= duration {
                info!("Stopping TX generation after {duration:?}");
                break;
            }
        }
        if let Some(max_txs_num) = max_txs_num {
            if transaction_id == max_txs_num / num_connections {
                info!("Stopping TX generation at {max_txs_num}.");
                break;
            }
        }

        generate_dummy_data(
            &mut tx_buffer,
            transaction_id,
            timestamp(),
            identity,
            tx_size,
        );
        match tokio::time::timeout(
            Duration::from_millis(2500),
            send_data_over_stream(&connection, &tx_buffer[0..tx_size as usize]),
        )
        .await
        {
            Ok(Ok(_)) => {
                transaction_id += 1;
                if transaction_id % 1000 == 0 {
                    tracing::debug!("{:?}", &connection.stats());
                }
            }
            Ok(Err(e)) => {
                error!("Quic error {e}");
                break;
            }
            Err(_e) => {
                error!("Timeout sending stream ID {transaction_id}");
                //break;
            }
        }
        if time_between_txs * transaction_id.saturating_sub(1) as f64
            > start.elapsed().as_secs_f64()
        {
            tokio::time::sleep(Duration::from_micros(10)).await;
            dbg!("Throttling");
        }
    }

    // When the connection is closed all the streams that haven't been delivered yet will be lost.
    // Sleep to give it some time to deliver all the pending streams.
    sleep(Duration::from_secs(3)).await;

    let connection_stats = connection.stats();
    info!("client connection stats: {:?}", connection_stats);

    connection.close(0u32.into(), b"done");
    // Give the server a fair chance to receive the close packet
    endpoint.wait_idle().await;
    //let _ = feedback_reader.await;
    Ok(stats_collector)
}

/// return timestamp as ms
pub fn timestamp() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("create timestamp in timing")
        .as_millis() as u64
}
