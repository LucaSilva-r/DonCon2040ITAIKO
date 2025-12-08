#ifndef UTILS_SERIALCONFIG_H_
#define UTILS_SERIALCONFIG_H_

#include "utils/InputState.h"
#include "utils/SettingsStore.h"

#include "pico/stdlib.h"
#include "tusb.h"

#include <functional>

namespace Doncon::Utils {

/**
 * @brief Serial configuration interface for runtime parameter adjustment
 *
 * Provides a USB CDC serial protocol for reading and writing settings,
 * compatible with hidtaiko's web configurator (https://kasasiki3.github.io/ver1.3_webapp_rp2040version/).
 *
 * Protocol:
 * - Send "1000" to read all settings (returns "key:value" pairs)
 * - Send "1001" to save settings to flash
 * - Send "1002" to enter write mode
 * - Send "1003" to reload settings from flash
 * - Send "1004" to reboot to BOOTSEL mode
 * - Send "2000" to start streaming sensor data (CSV format)
 * - Send "2001" to stop streaming sensor data
 * - In write mode, send "key:value" pairs (e.g., "0:800")
 *
 * HIDtaiko-compatible Keys (web page order - note keys 0&1 swapped vs kando array!):
 * 0: Don Left Threshold (Left face sensitivity)
 * 1: Ka Left Threshold (Left rim sensitivity)
 * 2: Don Right Threshold (Right face sensitivity)
 * 3: Ka Right Threshold (Right rim sensitivity)
 * 4: Don Debounce (Don-to-Don lockout time)
 * 5: Ka Debounce (Ka-to-Ka lockout time)
 * 6: Crosstalk Debounce (Don-to-Ka lockout time)
 * 7: Key Release Timeout (Key press duration sent to PC)
 * 8: Individual key debounce (Global signal hold time)
 *
 * Extended Keys (DonCon2040-specific, not in hidtaiko):
 * 9: Double Trigger Mode (0=Off, 1=Threshold)
 * 10: Double Trigger Don Left Threshold
 * 11: Double Trigger Ka Left Threshold
 * 12: Double Trigger Don Right Threshold
 * 13: Double Trigger Ka Right Threshold
 * 14: Cutoff Don Left Threshold
 * 15: Cutoff Ka Left Threshold
 * 16: Cutoff Don Right Threshold
 * 17: Cutoff Ka Right Threshold
 * 18: Drum P1 Ka Left Key (HID keycode)
 * 19: Drum P1 Don Left Key (HID keycode)
 * 20: Drum P1 Don Right Key (HID keycode)
 * 21: Drum P1 Ka Right Key (HID keycode)
 * 22: Drum P2 Ka Left Key (HID keycode)
 * 23: Drum P2 Don Left Key (HID keycode)
 * 24: Drum P2 Don Right Key (HID keycode)
 * 25: Drum P2 Ka Right Key (HID keycode)
 * 26: Controller Up Key (HID keycode)
 * 27: Controller Down Key (HID keycode)
 * 28: Controller Left Key (HID keycode)
 * 29: Controller Right Key (HID keycode)
 * 30: Controller North Key (HID keycode)
 * 31: Controller East Key (HID keycode)
 * 32: Controller South Key (HID keycode)
 * 33: Controller West Key (HID keycode)
 * 34: Controller L Key (HID keycode)
 * 35: Controller R Key (HID keycode)
 * 36: Controller Start Key (HID keycode)
 * 37: Controller Select Key (HID keycode)
 * 38: Controller Home Key (HID keycode)
 * 39: Controller Share Key (HID keycode)
 * 40: Controller L3 Key (HID keycode)
 * 41: Controller R3 Key (HID keycode)
 * 42: ADC Channel Don Left (0-3)
 * 43: ADC Channel Ka Left (0-3)
 * 44: ADC Channel Don Right (0-3)
 * 45: ADC Channel Ka Right (0-3)
 *
 * Special Output:
 * Version:Firmware Version String (e.g. "Version:0.0.0")
 */
class SerialConfig {
  public:
    using SettingsAppliedCallback = std::function<void()>;

    explicit SerialConfig(SettingsStore &settings_store, SettingsAppliedCallback on_settings_applied = nullptr);

    /**
     * @brief Process incoming serial data
     *
     * Call this from main loop when CDC data is available.
     * Non-blocking, processes one command per call.
     */
    void processSerial();

    /**
     * @brief Send sensor data if streaming is active
     *
     * Call this from main loop after processSerial().
     * Sends CSV-formatted sensor data when streaming mode is enabled.
     *
     * @param input_state Current input state containing sensor data
     */
    void sendSensorDataIfStreaming(const InputState &input_state);

  private:
    SettingsStore &m_settings_store;
    SettingsAppliedCallback m_on_settings_applied;
    bool m_write_mode;
    int m_write_count;
    bool m_streaming_mode;
    uint64_t m_last_stream_time;

    // ADC streaming average data
    uint32_t m_don_left_sum;
    uint32_t m_ka_left_sum;
    uint32_t m_don_right_sum;
    uint32_t m_ka_right_sum;
    uint32_t m_sample_count;

    enum class Command : int {
        ReadAll = 1000,
        SaveToFlash = 1001,
        EnterWriteMode = 1002,
        ReloadFromFlash = 1003,
        RebootToBootsel = 1004,
        StartStreaming = 2000,
        StopStreaming = 2001,
    };

    void handleCommand(int command_value);
    void handleWriteData(const char *data);
    void sendAllSettings();
    void sendSensorData(const InputState &input_state, uint16_t ka_l, uint16_t don_l, uint16_t don_r, uint16_t ka_r);
    uint16_t getSettingByKey(int key);
    void setSettingByKey(int key, uint16_t value);
};

} // namespace Doncon::Utils

#endif // UTILS_SERIALCONFIG_H_
