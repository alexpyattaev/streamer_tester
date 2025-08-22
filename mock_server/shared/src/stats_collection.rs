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

#[derive(Clone, Copy, Debug)]
pub struct StatsSample {
    pub udp_tx: u64,
    pub udp_rx: u64,
    pub time_stamp: u64,
}

#[derive(Clone, Debug)]
pub struct StatsCollection(pub Vec<StatsSample>);

impl StatsCollection {
    pub fn new() -> StatsCollection {
        StatsCollection(Vec::new())
    }

    pub fn push(&mut self, sample: StatsSample) {
        self.0.push(sample);
    }

    pub fn write_csv(&self, host: String) {
        let file_name = format!("{}-host-netstats.csv", host);
        let mut path = std::path::PathBuf::from("results");
        path.push(file_name);
        let file = std::fs::File::create(path).unwrap();
        let mut csv_writer = csv::Writer::from_writer(file);
        csv_writer
            .write_record(&["udp_tx", "udp_rx", "time_stamp"])
            .unwrap();
        for stat in &self.0 {
            csv_writer
                .serialize((stat.udp_tx, stat.udp_rx, stat.time_stamp))
                .unwrap();
        }
        let _ = csv_writer.flush();
    }
}

impl IntoIterator for StatsCollection {
    type Item = StatsSample;
    type IntoIter = std::vec::IntoIter<StatsSample>;

    fn into_iter(self) -> Self::IntoIter {
        self.0.into_iter()
    }
}

pub fn file_bin(host: String) -> Option<std::io::BufWriter<std::fs::File>> {
    let file_name = format!("{}-host-transactions.bin", host);
    let mut path = std::path::PathBuf::from("results");
    path.push(file_name);
    let file = std::fs::File::create(path).unwrap();
    let file = std::io::BufWriter::with_capacity(10 * 1024, file);
    Some(file)
}
