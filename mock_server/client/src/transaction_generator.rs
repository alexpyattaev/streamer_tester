pub fn generate_dummy_data(buffer: &mut [u8], transaction_id: usize, timestamp: u64, _size: u64) {
    buffer[0..8].copy_from_slice(&transaction_id.to_le_bytes());

    buffer[8..16].copy_from_slice(&timestamp.to_le_bytes());
    // we can fill in the rest with some data but I think there is enough entropy due to tx_id and timestamp
}
