use std::{sync::atomic::AtomicU64, time::Instant};

use quinn::{
    congestion::{Controller, ControllerFactory},
    crypto::rustls::QuicClientConfig,
    ClientConfig, Connection, Endpoint, IdleTimeout, TransportConfig,
};
use quinn_proto::RttEstimator;
use rustls::KeyLogFile;
use solana_sdk::signature::Keypair;
//use std::sync::atomic::Ordering::Relaxed;

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
#[derive(Debug, Clone)]
struct NopCongestion {
    pub window_size: u64,
    pub last_congestion: Instant,
    pub last_increase: Instant,
}

impl NopCongestion {
    const MIN_WINDOW_SIZE: u64 = 8_000_000 / 2;
    const MAX_WINDOW_SIZE: u64 = 8_000_000;
    const ADJUST_INTERVAL: Duration = Duration::from_millis(5);

    pub fn new() -> Self {
        Self {
            window_size: Self::MIN_WINDOW_SIZE,
            last_congestion: Instant::now(),
            last_increase: Instant::now(),
        }
    }
}

impl Controller for NopCongestion {
    fn on_mtu_update(&mut self, _: u16) {}
    fn window(&self) -> u64 {
        // self.window_size
        Self::MAX_WINDOW_SIZE
    }
    fn clone_box(&self) -> Box<(dyn Controller + 'static)> {
        Box::new(self.clone())
    }
    fn initial_window(&self) -> u64 {
        Self::MIN_WINDOW_SIZE
    }
    fn into_any(self: Box<Self>) -> Box<(dyn std::any::Any + 'static)> {
        Box::new(self)
    }

    fn on_congestion_event(
        &mut self,
        _now: Instant,
        _sent: Instant,
        _is_persistent_congestion: bool,
        _lost_bytes: u64,
    ) {
        let now = Instant::now();
        let dt = now.duration_since(self.last_congestion);
        if dt > Self::ADJUST_INTERVAL {
            self.last_congestion = now;
            self.last_increase = now; // prevent from immediately improving
            self.window_size = (self.window_size / 2).max(Self::MIN_WINDOW_SIZE);
            println!("Window is {}", self.window_size);
        }
    }

    fn on_ack(
        &mut self,
        _now: Instant,
        _sent: Instant,
        _bytes: u64,
        _app_limited: bool,
        rtt: &RttEstimator,
    ) {
        if self.window_size == Self::MAX_WINDOW_SIZE {
            return;
        }
        let now = Instant::now();
        let dt = now.duration_since(self.last_increase);
        if dt > rtt.get() {
            self.last_increase = now;
            self.window_size = (self.window_size * 2).min(Self::MAX_WINDOW_SIZE);
            println!("Window is {}", self.window_size);
        }
    }
}
impl ControllerFactory for NopCongestion {
    fn build(self: Arc<Self>, _: std::time::Instant, _: u16) -> Box<(dyn Controller + 'static)> {
        Box::new(Self::new())
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
    crypto.key_log = Arc::new(KeyLogFile::new());
    let mut config = ClientConfig::new(Arc::new(QuicClientConfig::try_from(crypto).unwrap()));
    let mut transport_config = TransportConfig::default();

    let timeout = IdleTimeout::try_from(QUIC_MAX_TIMEOUT).unwrap();
    transport_config.max_idle_timeout(Some(timeout));
    transport_config.keep_alive_interval(Some(QUIC_KEEP_ALIVE));
    transport_config.send_fairness(QUIC_SEND_FAIRNESS);
    if no_congestion {
        transport_config.congestion_controller_factory(Arc::new(NopCongestion::new()));
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
) -> Result<u64, QuicClientError> {
    let mut send_stream = connection.open_uni().await?;
    let stream_id = send_stream.id().index();
    send_stream.write_all(data).await?;
    // never do this (c) Alessandro
    //let _ = send_stream.finish();

    Ok(stream_id)
}

#[derive(Debug, Default)]
pub struct ConnectionState {
    pub server_last_started_stream: AtomicU64,
    pub server_last_completed_stream: AtomicU64,
    pub client_last_started_stream: AtomicU64,
    pub client_last_completed_stream: AtomicU64,
    pub server_completed_streams: AtomicU64,
    pub client_completed_streams: AtomicU64,
}
