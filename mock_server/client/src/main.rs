#![allow(clippy::arithmetic_side_effects)]
//! This example demonstrates an HTTP client that requests files from a server.
//!
//! Checkout the `README.md` for guidance.

use quinn::ClientConfig;
use shared::stats_collection::{file_bin, StatsCollection, StatsSample};
use solana_sdk::{pubkey::Pubkey, signer::Signer};
use std::io::Write as _;
use tracing::trace;
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

#[tokio::main]
async fn run(parameters: ClientCliParameters) -> Result<(), QuicClientError> {
    let identity = if let Some(staked_identity_file) = parameters.staked_identity_file.clone() {
        Keypair::read_from_file(staked_identity_file)
            .map_err(|_err| QuicClientError::KeypairReadFailure)?
    } else {
        Keypair::new()
    };
    let client_certificate = Arc::new(QuicClientCertificate::new(&identity));
    let client_config = create_client_config(client_certificate, parameters.disable_congestion);
    let result = run_endpoint(
        client_config,
        parameters.clone(),
        identity.pubkey(),
        parameters.host_name.clone().as_ref(),
    )
    .await;
    match result {
        Ok(collection) => {
            if let Some(host_name) = parameters.host_name.clone() {
                collection.write_csv(host_name);
            }
        }
        Err(e) => println!("{e}"),
    }

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
    host_name: Option<&String>,
) -> Result<StatsCollection, QuicClientError> {
    let endpoint =
        create_client_endpoint(bind, client_config).expect("Endpoint creation should not fail.");

    let connection = endpoint.connect(target, "connect")?.await?;

    let mut stats_collector: StatsCollection = StatsCollection::new();
    let mut stats_dt: u64;

    let mut file_binary_log = if let Some(host_name) = host_name {
        file_bin(host_name.into())
    } else {
        None
    };
    let start = Instant::now();
    let mut transaction_id = 0;
    let mut tx_buffer = [0u8; PACKET_DATA_SIZE];
    let mut stat_buff: Vec<u32> = Vec::new();
    let max_bitrate_mbps = 100e6;
    let time_between_txs = (tx_size * 8) as f64 / max_bitrate_mbps;
    loop {
        let con_stats = connection.stats();
        stats_dt = start.elapsed().as_micros() as u64;
        let stats = StatsSample {
            udp_tx: con_stats.udp_tx.bytes,
            udp_rx: con_stats.udp_rx.bytes,
            time_stamp: stats_dt,
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
            Duration::from_millis(500),
            send_data_over_stream(&connection, &tx_buffer[0..tx_size as usize], start),
        )
        .await
        {
            Ok(Ok(dt)) => {
                transaction_id += 1;
                stat_buff.push(dt);
            }
            Ok(Err(e)) => {
                println!("Quic error {e}");
                break;
            }
            Err(_e) => {
                trace!("Timeout sending stream, skipping");
            }
        }
        if time_between_txs * transaction_id as f64 > start.elapsed().as_secs_f64() {
            tokio::time::sleep(Duration::from_millis(10)).await;
        }
    }

    if let Some(writer) = file_binary_log.as_mut() {
        for val in &stat_buff {
            writer.write_all(&val.to_ne_bytes()).unwrap();
        }
        writer.flush().unwrap();
    }
    // When the connection is closed all the streams that haven't been delivered yet will be lost.
    // Sleep to give it some time to deliver all the pending streams.
    sleep(Duration::from_secs(1)).await;

    let connection_stats = connection.stats();
    info!("client connection stats: {:?}", connection_stats);
    info!("TRANSACTIONS_SENT {}", transaction_id);
    if let Some(host_name) = host_name {
        let mut num_sent_file =
            std::fs::File::create(format!("results/{}.summary", host_name)).unwrap();
        num_sent_file
            .write_all(&transaction_id.to_ne_bytes())
            .unwrap();
    }

    connection.close(0u32.into(), b"done");
    // Give the server a fair chance to receive the close packet
    endpoint.wait_idle().await;
    Ok(stats_collector)
}

/// return timestamp as ms
pub fn timestamp() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("create timestamp in timing")
        .as_millis() as u64
}
