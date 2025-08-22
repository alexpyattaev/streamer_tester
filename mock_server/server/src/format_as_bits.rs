pub fn format_as_bits(size_in_bytes: f64) -> String {
    let bits = size_in_bytes * 8.0; // Convert bytes to bits

    // Use 1024 as the base for binary conversion
    const KILOBIT: f64 = 1024.0;
    const MEGABIT: f64 = 1024.0 * KILOBIT;
    const GIGABIT: f64 = 1024.0 * MEGABIT;

    if bits >= GIGABIT {
        format!("{:.2} Gb/s", bits / GIGABIT) // Convert to gigabits
    } else if bits >= MEGABIT {
        format!("{:.2} Mb/s", bits / MEGABIT) // Convert to megabits
    } else if bits >= KILOBIT {
        format!("{:.2} Kb/s", bits / KILOBIT) // Convert to kilobits
    } else {
        format!("{:.2} bits/s", bits) // Less than 1 Kb, just print bits
    }
}
