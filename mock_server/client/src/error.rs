use quinn::{ConnectError, ConnectionError, WriteError};

use {std::io, thiserror::Error};

// called QuicError in agave
#[derive(Error, Debug)]
pub enum QuicClientError {
    #[error(transparent)]
    WriteError(#[from] WriteError),
    #[error(transparent)]
    ConnectionError(#[from] ConnectionError),
    #[error(transparent)]
    ConnectError(#[from] ConnectError),

    #[error(transparent)]
    EndpointError(#[from] io::Error),

    #[error("Failed to read keypair file")]
    KeypairReadFailure,
}
