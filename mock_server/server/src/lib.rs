pub mod cli;
pub mod format_as_bits;
pub mod packet_accumulator;
pub mod tls_certificates;

use quinn::{crypto::rustls::NoInitialCipherSuite, ConnectionError};

use {
    rustls::{
        pki_types::{CertificateDer, UnixTime},
        server::danger::ClientCertVerified,
        DistinguishedName,
    },
    std::{io, sync::Arc, time::Duration},
    thiserror::Error,
};

// Empirically found max number of concurrent streams
// that seems to maximize TPS on GCE (higher values don't seem to
// give significant improvement or seem to impact stability)
pub const QUIC_MAX_UNSTAKED_CONCURRENT_STREAMS: usize = 128;

pub const QUIC_MAX_STAKED_CONCURRENT_STREAMS: usize = 512;
// the same is in the client crate
pub const QUIC_MAX_TIMEOUT: Duration = Duration::from_secs(2);

/*#[derive(Error, Debug)]
pub struct FailedReadChunk;

impl fmt::Display for FailedReadChunk {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "Failed to read chunk")
    }
}*/

#[derive(Error, Debug)]
pub enum QuicServerError {
    #[error("Endpoint creation failed: {0}")]
    EndpointFailed(io::Error),
    #[error("TLS error: {0}")]
    TlsError(#[from] rustls::Error),
    #[error("No initial cipher suite")]
    NoInitialCipherSuite(#[from] NoInitialCipherSuite),
    #[error(transparent)]
    ConnectionError(#[from] ConnectionError),
    #[error("Failed to read chunk")]
    FailedReadChunk,
    #[error(transparent)]
    EndpointError(#[from] io::Error),
}

#[derive(Debug)]
pub struct SkipClientVerification(Arc<rustls::crypto::CryptoProvider>);

impl SkipClientVerification {
    pub fn new() -> Arc<Self> {
        Arc::new(Self(Arc::new(rustls::crypto::ring::default_provider())))
    }
}

impl rustls::server::danger::ClientCertVerifier for SkipClientVerification {
    fn verify_client_cert(
        &self,
        _end_entity: &CertificateDer,
        _intermediates: &[CertificateDer],
        _now: UnixTime,
    ) -> Result<ClientCertVerified, rustls::Error> {
        Ok(rustls::server::danger::ClientCertVerified::assertion())
    }

    fn root_hint_subjects(&self) -> &[DistinguishedName] {
        &[]
    }

    fn verify_tls12_signature(
        &self,
        message: &[u8],
        cert: &rustls::pki_types::CertificateDer<'_>,
        dss: &rustls::DigitallySignedStruct,
    ) -> Result<rustls::client::danger::HandshakeSignatureValid, rustls::Error> {
        rustls::crypto::verify_tls12_signature(
            message,
            cert,
            dss,
            &self.0.signature_verification_algorithms,
        )
    }

    fn verify_tls13_signature(
        &self,
        message: &[u8],
        cert: &rustls::pki_types::CertificateDer<'_>,
        dss: &rustls::DigitallySignedStruct,
    ) -> Result<rustls::client::danger::HandshakeSignatureValid, rustls::Error> {
        rustls::crypto::verify_tls13_signature(
            message,
            cert,
            dss,
            &self.0.signature_verification_algorithms,
        )
    }

    fn supported_verify_schemes(&self) -> Vec<rustls::SignatureScheme> {
        self.0.signature_verification_algorithms.supported_schemes()
    }

    fn offer_client_auth(&self) -> bool {
        true
    }

    fn client_auth_mandatory(&self) -> bool {
        self.offer_client_auth()
    }
}
