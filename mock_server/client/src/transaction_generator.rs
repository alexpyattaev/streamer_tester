use solana_sdk::pubkey::Pubkey;

pub fn generate_dummy_data(
    buffer: &mut [u8],
    transaction_id: usize,
    timestamp: u64,
    identity: Pubkey,
    _size: u64,
) {
    buffer[0 ..32].copy_from_slice(identity.as_array());
    buffer[32..32+8].copy_from_slice(&transaction_id.to_le_bytes());

    buffer[32+8..32+16].copy_from_slice(&timestamp.to_le_bytes());

    // we can fill in the rest with some data but I think there is enough entropy due to tx_id and timestamp
}
