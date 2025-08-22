//! Copy pasted from agave nonblocking/quic.rs
use {bytes::Bytes, smallvec::SmallVec, solana_sdk::packet::Meta, std::time::Instant};
// A sequence of bytes that is part of a packet
// along with where in the packet it is
pub struct PacketChunk {
    pub bytes: Bytes,
    // The offset of these bytes in the Quic stream
    // and thus the beginning offset in the slice of the
    // Packet data array into which the bytes will be copied
    pub offset: usize,
    // The end offset of these bytes in the Quic stream
    // and thus the end of the slice in the Packet data array
    // into which the bytes will be copied
    pub end_of_chunk: usize,
}

// A struct to accumulate the bytes making up
// a packet, along with their offsets, and the
// packet metadata. We use this accumulator to avoid
// multiple copies of the Bytes (when building up
// the Packet and then when copying the Packet into a PacketBatch)
pub struct PacketAccumulator {
    pub meta: Meta,
    pub chunks: SmallVec<[PacketChunk; 2]>,
    pub start_time: Instant,
}
