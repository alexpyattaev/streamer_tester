// Original connection.stats() structure
// connection.stats():ConnectionStats { udp_tx: UdpStats { datagrams: 3, bytes: 3726, ios: 3 }, udp_rx: UdpStats { datagrams: 2, bytes: 1338, ios: 3 },
// frame_tx: FrameStats { ACK: 2, ACK_FREQUENCY: 0, CONNECTION_CLOSE: 0, CRYPTO: 2, DATA_BLOCKED: 0, DATAGRAM: 0, HANDSHAKE_DONE: 0, IMMEDIATE_ACK: 1, MAX_DATA: 0,
// MAX_STREAM_DATA: 0, MAX_STREAMS_BIDI: 0, MAX_STREAMS_UNI: 0, NEW_CONNECTION_ID: 0, NEW_TOKEN: 0, PATH_CHALLENGE: 0, PATH_RESPONSE: 0, PING: 1, RESET_STREAM: 0,
// RETIRE_CONNECTION_ID: 0, STREAM_DATA_BLOCKED: 0, STREAMS_BLOCKED_BIDI: 0, STREAMS_BLOCKED_UNI: 0, STOP_SENDING: 0, STREAM: 0 },
// frame_rx: FrameStats { ACK: 1, ACK_FREQUENCY: 0, CONNECTION_CLOSE: 0, CRYPTO: 2, DATA_BLOCKED: 0, DATAGRAM: 0, HANDSHAKE_DONE: 0, IMMEDIATE_ACK: 0, MAX_DATA: 0,
// MAX_STREAM_DATA: 0, MAX_STREAMS_BIDI: 0, MAX_STREAMS_UNI: 0, NEW_CONNECTION_ID: 4, NEW_TOKEN: 0, PATH_CHALLENGE: 0, PATH_RESPONSE: 0, PING: 0, RESET_STREAM: 0,
// RETIRE_CONNECTION_ID: 0, STREAM_DATA_BLOCKED: 0, STREAMS_BLOCKED_BIDI: 0, STREAMS_BLOCKED_UNI: 0, STOP_SENDING: 0, STREAM: 0 },
// path: PathStats { rtt: 3.461059ms, cwnd: 12000, congestion_events: 0, lost_packets: 0, lost_bytes: 0, sent_packets: 4, sent_plpmtud_probes: 1,
// lost_plpmtud_probes: 0, black_holes_detected: 0, current_mtu: 1200 } }

use bytemuck::{AnyBitPattern, NoUninit};
#[derive(Clone, Copy, Debug, AnyBitPattern, NoUninit)]
#[repr(C)]
pub struct StatsSample {
    pub udp_tx: u64,
    pub udp_rx: u64,
    pub congestion_events: u64,
    pub lost_packets: u64,
    pub time_stamp: u64,
    pub connection_id: u64,
}

pub fn file_bin(host: String) -> anyhow::Result<std::io::BufWriter<std::fs::File>> {
    let file_name = format!("{}-host-transactions.bin", host);
    let mut path = std::path::PathBuf::from("results");
    path.push(file_name);
    let file = std::fs::File::create(path)?;
    let file = std::io::BufWriter::with_capacity(1024 * 1024, file);
    Ok(file)
}
