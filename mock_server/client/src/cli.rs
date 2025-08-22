use {
    clap::{crate_description, crate_name, crate_version, Parser},
    std::{net::SocketAddr, path::PathBuf, time::Duration},
};

#[derive(Parser, Debug, Clone)]
#[clap(name = crate_name!(),
    version = crate_version!(),
    about = crate_description!(),
    rename_all = "kebab-case"
)]
pub struct ClientCliParameters {
    #[clap(long, help = "Target IP:PORT", default_value = "127.0.0.1:4433")]
    pub target: SocketAddr,

    // Cannot use value_parser to read keypair file because Keypair is not Clone.
    #[clap(long, help = "validator identity for staked connection")]
    pub staked_identity_file: Option<PathBuf>,

    /// Address to bind on, default will listen on all available interfaces, 0 that
    /// OS will choose the port.
    #[clap(long, help = "bind", default_value = "0.0.0.0:0")]
    pub bind: SocketAddr,

    #[clap(
        long,
        value_parser = parse_duration,
        help = "If specified, limits the benchmark execution to the specified duration in seconds."
    )]
    pub duration: Option<Duration>,

    #[clap(
        long,
        conflicts_with = "duration",
        help = "If specified, limits the benchmark execution to the specified number of transactions.\
        Each connection will send `max_txs_num/num_connections` transactions, `max_txs_num` must be divisible by `num_connections`."
    )]
    pub max_txs_num: Option<usize>,

    // it is u64 (instead of usize) because clap value parser doesn't
    // work properly with usize.
    #[clap(long,
        value_parser = clap::value_parser!(u64).range(16..1232),
        help = "Size of transaction in bytes.", default_value = "251")]
    pub tx_size: u64,

    #[clap(
        long,
        help = "Number of concurrent connections each in it's own tokio task",
        default_value = "1"
    )]
    pub num_connections: usize,

    #[clap(long, help = "Disable congestion control")]
    pub disable_congestion: bool,

    #[clap(long, help = "Client's host name")]
    pub host_name: Option<String>,
}

fn parse_duration(s: &str) -> Result<Duration, &'static str> {
    s.parse::<f64>()
        .map(Duration::from_secs_f64)
        .map_err(|_| "failed to parse duration")
}

pub fn build_cli_parameters() -> ClientCliParameters {
    let parameters = ClientCliParameters::parse();
    if let Some(num_txs) = parameters.max_txs_num {
        if num_txs % parameters.num_connections != 0 {
            eprintln!(
                "Error: num_txs ({}) is not divisible by num_connections ({}).",
                num_txs, parameters.num_connections
            );
            std::process::exit(1);
        }
    }
    parameters
}
