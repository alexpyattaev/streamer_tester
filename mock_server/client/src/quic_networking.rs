use quinn::{
    congestion::{Controller, ControllerFactory},
    crypto::rustls::QuicClientConfig,
    ClientConfig, Connection, Endpoint, IdleTimeout, TransportConfig,
};
use solana_sdk::signature::Keypair;
use tokio::time::Instant;

use {
    crate::error::QuicClientError,
    server::tls_certificates::new_dummy_x509_certificate,
    solana_streamer::nonblocking::quic::ALPN_TPU_PROTOCOL_ID,
    std::{net::SocketAddr, sync::Arc, time::Duration},
};

const QUIC_MAX_TIMEOUT: Duration = Duration::from_secs(2);
// TODO(klykov): it think the ratio between these consts should be higher
const QUIC_KEEP_ALIVE: Duration = Duration::from_secs(1);

#[derive(Debug)]
pub struct SkipServerVerification(Arc<rustls::crypto::CryptoProvider>);

impl SkipServerVerification {
    pub fn new() -> Arc<Self> {
        Arc::new(Self(Arc::new(rustls::crypto::ring::default_provider())))
    }
}

impl rustls::client::danger::ServerCertVerifier for SkipServerVerification {
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

    fn verify_server_cert(
        &self,
        _end_entity: &rustls::pki_types::CertificateDer<'_>,
        _intermediates: &[rustls::pki_types::CertificateDer<'_>],
        _server_name: &rustls::pki_types::ServerName<'_>,
        _ocsp_response: &[u8],
        _now: rustls::pki_types::UnixTime,
    ) -> Result<rustls::client::danger::ServerCertVerified, rustls::Error> {
        Ok(rustls::client::danger::ServerCertVerified::assertion())
    }
}

pub struct QuicClientCertificate {
    pub certificate: rustls::pki_types::CertificateDer<'static>,
    pub key: rustls::pki_types::PrivateKeyDer<'static>,
}

impl Default for QuicClientCertificate {
    fn default() -> Self {
        QuicClientCertificate::new(&Keypair::new())
    }
}

// adapted from `impl Default for QuicLazyInitializedEndpoint`
impl QuicClientCertificate {
    pub fn new(keypair: &Keypair) -> Self {
        let (certificate, key) = new_dummy_x509_certificate(keypair);
        Self { certificate, key }
    }
}

struct NopCongestion;
impl Controller for NopCongestion {
    fn on_congestion_event(
        &mut self,
        _: std::time::Instant,
        _: std::time::Instant,
        _: bool,
        _: u64,
    ) {
    }
    fn on_mtu_update(&mut self, _: u16) {}
    fn window(&self) -> u64 {
        return 10000000;
    }
    fn clone_box(&self) -> Box<(dyn Controller + 'static)> {
        Box::new(Self)
    }
    fn initial_window(&self) -> u64 {
        return 10000000;
    }
    fn into_any(self: Box<Self>) -> Box<(dyn std::any::Any + 'static)> {
        Box::new(self)
    }
}
impl ControllerFactory for NopCongestion {
    fn build(self: Arc<Self>, _: std::time::Instant, _: u16) -> Box<(dyn Controller + 'static)> {
        Box::new(Self)
    }
}

// Disable Quic send fairness.
// When set to false, streams are still scheduled based on priority,
// but once a chunk of a stream has been written out, quinn tries to complete
// the stream instead of trying to round-robin balance it among the streams
// with the same priority.
// See https://github.com/quinn-rs/quinn/pull/2002.
pub const QUIC_SEND_FAIRNESS: bool = false;

// taken from QuicLazyInitializedEndpoint::create_endpoint
pub fn create_client_config(
    client_certificate: Arc<QuicClientCertificate>,
    no_congestion: bool,
) -> ClientConfig {
    let mut crypto = rustls::ClientConfig::builder()
        .dangerous()
        .with_custom_certificate_verifier(SkipServerVerification::new())
        .with_client_auth_cert(
            vec![client_certificate.certificate.clone()],
            client_certificate.key.clone_key(),
        )
        .expect("Failed to set QUIC client certificates");
    crypto.enable_early_data = true;
    crypto.alpn_protocols = vec![ALPN_TPU_PROTOCOL_ID.to_vec()];

    let mut config = ClientConfig::new(Arc::new(QuicClientConfig::try_from(crypto).unwrap()));
    let mut transport_config = TransportConfig::default();

    let timeout = IdleTimeout::try_from(QUIC_MAX_TIMEOUT).unwrap();
    transport_config.max_idle_timeout(Some(timeout));
    transport_config.keep_alive_interval(Some(QUIC_KEEP_ALIVE));
    transport_config.send_fairness(QUIC_SEND_FAIRNESS);
    if no_congestion {
        transport_config.congestion_controller_factory(Arc::new(NopCongestion));
    }
    config.transport_config(Arc::new(transport_config));

    config
}

pub fn create_client_endpoint(
    bind_addr: SocketAddr,
    client_config: ClientConfig,
) -> Result<Endpoint, QuicClientError> {
    let mut endpoint = Endpoint::client(bind_addr)?;
    endpoint.set_default_client_config(client_config);
    Ok(endpoint)
}

// was called _send_buffer_using_conn
pub async fn send_data_over_stream(
    connection: &Connection,
    data: &[u8],
    start: std::time::Instant,
) -> Result<u32, QuicClientError> {
    let mut send_stream = connection.open_uni().await?;

    send_stream.write_all(data).await?;
    //never do this
    let _ = send_stream.finish();
    let dt = start.elapsed().as_micros() as u32;

    Ok(dt)
}
