use {
    clap::{crate_description, crate_name, crate_version, Parser},
    std::net::SocketAddr,
};

#[derive(Parser, Debug)]
#[clap(name = crate_name!(),
    version = crate_version!(),
    about = crate_description!(),
    rename_all = "kebab-case"
)]
pub struct ServerCliParameters {
    /// Enable stateless retries
    #[clap(long)]
    pub stateless_retry: bool,
    /// Address to listen on
    #[clap(long = "listen", default_value = "127.0.0.1:4433")]
    pub listen: SocketAddr,

    /// Maximum number of concurrent connections to allow
    #[clap(long)]
    pub connection_limit: Option<usize>,

    /// max concurrent streams
    /// QUIC_MAX_STAKED_CONCURRENT_STREAMS = 512
    #[clap(long, default_value = "512")]
    pub max_concurrent_streams: u32,

    // PACKET_DATA_SIZE = 1232
    #[clap(long, default_value = "1232")]
    pub stream_receive_window_size: u32,

    #[clap(long, default_value = "12320")]
    pub receive_window_size: u32,

    #[clap(
        long,
        help = "Write reordering log file if specified. The exact file name will be \
        `<reordering_log_file>-<connection_id>.csv`. The log has the following columns: \
        `[timestamp, max_seen_tx_id, timestamp_max_seen_ms, current_tx_id, timestamp_current_ms]`. \
        `timestamp` is the server timestamp. `max_seen_tx_id` identifies the max transaction ID \
        received so far, while `timestamp_max_seen_ms` is the corresponding timestamp."
    )]
    pub reordering_log_file: Option<String>,

    /// Transactions log to bin u32 (microsecs since thread start)
    #[clap(long)]
    pub log: bool,
}

pub fn build_cli_parameters() -> ServerCliParameters {
    ServerCliParameters::parse()
}
