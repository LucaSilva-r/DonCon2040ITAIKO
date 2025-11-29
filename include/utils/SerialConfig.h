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
 * - Send "2000" to start streaming sensor data (CSV format)
 * - Send "2001" to stop streaming sensor data
 * - In write mode, send "key:value" pairs (e.g., "0:800")
 *
 * HIDtaiko-compatible Keys (web page order - note keys 0&1 swapped vs kando array!):
 * 0: Don Left Threshold (Left face sensitivity)
 * 1: Ka Left Threshold (Left rim sensitivity)
 * 2: Don Right Threshold (Right face sensitivity)
 * 3: Ka Right Threshold (Right rim sensitivity)
 * 4: Don Debounce - B delay (Next input time after face hit)
 * 5: Kat Debounce - C delay (Rim input acceptance time)
 * 6: Crosstalk Debounce - D delay (Time to ignore rim after face)
 * 7: Key Timeout - H delay (Input limit for simulators)
 * 8: Debounce Delay - A delay (Key hold time)
 *
 * Extended Keys (DonCon2040-specific, not in hidtaiko):
 * 9: Double Trigger Mode (0=Off, 1=Threshold)
 * 10: Double Trigger Don Left Threshold
 * 11: Double Trigger Ka Left Threshold
 * 12: Double Trigger Don Right Threshold
 * 13: Double Trigger Ka Right Threshold
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
