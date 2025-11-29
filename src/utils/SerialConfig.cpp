#include "utils/SerialConfig.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace Doncon::Utils {

namespace {
char s_serial_buf[256];
uint32_t s_serial_buf_idx = 0;
} // namespace

SerialConfig::SerialConfig(SettingsStore &settings_store, SettingsAppliedCallback on_settings_applied)
    : m_settings_store(settings_store), m_on_settings_applied(on_settings_applied), m_write_mode(false),
      m_write_count(0), m_streaming_mode(false), m_last_stream_time(0), m_don_left_sum(0), m_ka_left_sum(0),
      m_don_right_sum(0), m_ka_right_sum(0), m_sample_count(0) {}

void SerialConfig::processSerial() {
    if (!tud_cdc_connected()) {
        return;
    }

    // Read characters into our buffer
    while (tud_cdc_available() && s_serial_buf_idx < sizeof(s_serial_buf) - 1) {
        char c;
        uint32_t count = tud_cdc_read(&c, 1);
        if (count == 0) {
            continue;
        }

        if (c == '\n' || c == '\r') {
            if (s_serial_buf_idx > 0) {
                s_serial_buf[s_serial_buf_idx] = '\0'; // Null terminate
                // We have a complete line
                if (m_write_mode) {
                    handleWriteData(s_serial_buf);
                } else {
                    handleCommand(std::atoi(s_serial_buf));
                }
            }
            s_serial_buf_idx = 0; // Reset for next line
        } else {
            s_serial_buf[s_serial_buf_idx++] = c;
        }
    }

    if (s_serial_buf_idx >= sizeof(s_serial_buf) - 1) {
        // Buffer overflow, discard
        s_serial_buf_idx = 0;
    }
}

void SerialConfig::handleCommand(int command_value) {
    switch (static_cast<Command>(command_value)) {
    case Command::ReadAll:
        sendAllSettings();
        break;

    case Command::SaveToFlash:
        m_settings_store.store();
        stdio_flush();
        break;

    case Command::EnterWriteMode:
        m_write_mode = true;
        m_write_count = 0;
        break;

    case Command::ReloadFromFlash:
        // SettingsStore loads from flash on construction, so we just echo current values
        sendAllSettings();
        break;

    case Command::StartStreaming:
        m_streaming_mode = true;
        m_don_left_sum = 0;
        m_ka_left_sum = 0;
        m_don_right_sum = 0;
        m_ka_right_sum = 0;
        m_sample_count = 0;
        break;

    case Command::StopStreaming:
        m_streaming_mode = false;
        break;
    }
}

void SerialConfig::handleWriteData(const char *data) {
    char data_copy[256];
    strncpy(data_copy, data, sizeof(data_copy) - 1);
    data_copy[sizeof(data_copy) - 1] = '\0';

    char *saveptr;
    char *token = strtok_r(data_copy, " \n\r", &saveptr);

    while (token != NULL) {
        // Split on ':'
        char *colon = strchr(token, ':');
        if (colon) {
            *colon = '\0';
            int key = atoi(token);
            int value = atoi(colon + 1);

            setSettingByKey(key, value);

            m_write_count++;
        }
        token = strtok_r(NULL, " \n\r", &saveptr);
    }

    // Exit write mode after receiving at least one value.
    // The python script sends all values in one line.
    if (m_write_count > 0) {
        m_write_mode = false;
        m_write_count = 0;

        // Apply settings to Drum object by calling callback
        if (m_on_settings_applied) {
            m_on_settings_applied();
        }
    }
}

void SerialConfig::sendAllSettings() {
    // Send 14 values: 9 hidtaiko-compatible + 5 extended (double trigger)
    for (int i = 0; i < 14; i++) {
        uint16_t value = getSettingByKey(i);
        printf("%d:%d\n", i, value);
        stdio_flush();
        sleep_us(5000); // Small delay between values
    }
}

uint16_t SerialConfig::getSettingByKey(int key) {
    auto thresholds = m_settings_store.getTriggerThresholds();

    // HIDtaiko-compatible mapping (web page order, not kando array order!)
    switch (key) {
    case 0: // Don Left (face left sensitivity) - swapped!
        return thresholds.don_left;
    case 1: // Ka Left (rim left sensitivity) - swapped!
        return thresholds.ka_left;
    case 2: // Don Right (face right sensitivity)
        return thresholds.don_right;
    case 3: // Ka Right (rim right sensitivity)
        return thresholds.ka_right;
    case 4: // Don Debounce (B delay - next input time after face)
        return m_settings_store.getDonDebounceMs();
    case 5: // Kat Debounce (C delay - rim input acceptance time)
        return m_settings_store.getKatDebounceMs();
    case 6: // Crosstalk Debounce (D delay - time to ignore rim after face)
        return m_settings_store.getCrosstalkDebounceMs();
    case 7: // Key Timeout (H delay - input limit for simulators)
        return m_settings_store.getKeyTimeoutMs();
    case 8: // Debounce Delay (A delay - single hit acceptance time)
        return m_settings_store.getDebounceDelay();
    case 9: // Double Trigger Mode (0=Off, 1=Threshold)
        return static_cast<uint16_t>(m_settings_store.getDoubleTriggerMode());
    case 10: // Double Trigger Don Left Threshold
        return m_settings_store.getDoubleTriggerThresholds().don_left;
    case 11: // Double Trigger Ka Left Threshold
        return m_settings_store.getDoubleTriggerThresholds().ka_left;
    case 12: // Double Trigger Don Right Threshold
        return m_settings_store.getDoubleTriggerThresholds().don_right;
    case 13: // Double Trigger Ka Right Threshold
        return m_settings_store.getDoubleTriggerThresholds().ka_right;
    default:
        return 0;
    }
}

void SerialConfig::setSettingByKey(int key, uint16_t value) {
    auto thresholds = m_settings_store.getTriggerThresholds();
    auto double_thresholds = m_settings_store.getDoubleTriggerThresholds();

    // HIDtaiko-compatible mapping (web page order, not kando array order!)
    switch (key) {
    case 0: // Don Left (face left sensitivity) - swapped!
        thresholds.don_left = value;
        m_settings_store.setTriggerThresholds(thresholds);
        break;
    case 1: // Ka Left (rim left sensitivity) - swapped!
        thresholds.ka_left = value;
        m_settings_store.setTriggerThresholds(thresholds);
        break;
    case 2: // Don Right (face right sensitivity)
        thresholds.don_right = value;
        m_settings_store.setTriggerThresholds(thresholds);
        break;
    case 3: // Ka Right (rim right sensitivity)
        thresholds.ka_right = value;
        m_settings_store.setTriggerThresholds(thresholds);
        break;
    case 4: // Don Debounce (B delay)
        m_settings_store.setDonDebounceMs(value);
        break;
    case 5: // Kat Debounce (C delay)
        m_settings_store.setKatDebounceMs(value);
        break;
    case 6: // Crosstalk Debounce (D delay)
        m_settings_store.setCrosstalkDebounceMs(value);
        break;
    case 7: // Key Timeout (H delay)
        m_settings_store.setKeyTimeoutMs(value);
        break;
    case 8: // Debounce Delay (A delay)
        m_settings_store.setDebounceDelay(value);
        break;
    case 9: // Double Trigger Mode
        m_settings_store.setDoubleTriggerMode(static_cast<Peripherals::Drum::Config::DoubleTriggerMode>(value));
        break;
    case 10: // Double Trigger Don Left
        double_thresholds.don_left = value;
        m_settings_store.setDoubleTriggerThresholds(double_thresholds);
        break;
    case 11: // Double Trigger Ka Left
        double_thresholds.ka_left = value;
        m_settings_store.setDoubleTriggerThresholds(double_thresholds);
        break;
    case 12: // Double Trigger Don Right
        double_thresholds.don_right = value;
        m_settings_store.setDoubleTriggerThresholds(double_thresholds);
        break;
    case 13: // Double Trigger Ka Right
        double_thresholds.ka_right = value;
        m_settings_store.setDoubleTriggerThresholds(double_thresholds);
        break;
    default:
        break;
    }
}

void SerialConfig::sendSensorData(const InputState &input_state, uint16_t ka_l, uint16_t don_l, uint16_t don_r,
                                      uint16_t ka_r) {
    const auto &drum = input_state.drum;

    // CSV format:
    // triggered_ka_left,ka_raw,ka_duration,triggered_don_left,don_left_raw,don_left_duration,triggered_don_right,don_right_raw,don_right_duration,triggered_ka_right,ka_right_raw,ka_right_duration
    printf("%c,%d,%lu,%c,%d,%lu,%c,%d,%lu,%c,%d,%lu\n",                           //
           (drum.ka_left.triggered ? 'T' : 'F'), ka_l, drum.ka_left.duration_ms,   //
           (drum.don_left.triggered ? 'T' : 'F'), don_l, drum.don_left.duration_ms, //
           (drum.don_right.triggered ? 'T' : 'F'), don_r, drum.don_right.duration_ms,   //
           (drum.ka_right.triggered ? 'T' : 'F'), ka_r, drum.ka_right.duration_ms);
    stdio_flush();
}

void SerialConfig::sendSensorDataIfStreaming(const InputState &input_state) {
    if (!m_streaming_mode || !tud_cdc_connected()) {
        return;
    }

    // Accumulate sensor data
    m_don_left_sum += input_state.drum.don_left.raw;
    m_ka_left_sum += input_state.drum.ka_left.raw;
    m_don_right_sum += input_state.drum.don_right.raw;
    m_ka_right_sum += input_state.drum.ka_right.raw;
    m_sample_count++;

    // Rate limit to ~1000Hz (1ms between sends)
    const uint64_t current_time = time_us_64();
    if (current_time - m_last_stream_time < 1000) {
        return;
    }

    m_last_stream_time = current_time;

    if (m_sample_count > 0) {
        const uint16_t don_left_avg = m_don_left_sum / m_sample_count;
        const uint16_t ka_left_avg = m_ka_left_sum / m_sample_count;
        const uint16_t don_right_avg = m_don_right_sum / m_sample_count;
        const uint16_t ka_right_avg = m_ka_right_sum / m_sample_count;

        sendSensorData(input_state, ka_left_avg, don_left_avg, don_right_avg, ka_right_avg);

        // Reset accumulators
        m_don_left_sum = 0;
        m_ka_left_sum = 0;
        m_don_right_sum = 0;
        m_ka_right_sum = 0;
        m_sample_count = 0;
    }
}

} // namespace Doncon::Utils
