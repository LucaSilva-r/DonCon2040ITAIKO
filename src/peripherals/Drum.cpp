#include "peripherals/Drum.h"

#include "hardware/adc.h"
#include "pico/time.h"
#include <mcp3204/Mcp3204Dma.h>

#include <algorithm>
#include <cmath>

namespace Doncon::Peripherals {

Drum::InternalAdc::InternalAdc(const Config::InternalAdc &config) : m_config(config) {
    static const uint adc_base_pin = 26;

    for (uint pin = adc_base_pin; pin < adc_base_pin + 4; ++pin) {
        adc_gpio_init(pin);
    }

    adc_init();
}

std::array<uint16_t, 4> Drum::InternalAdc::read() {
    // if (m_config.sample_count == 0) {
    //     return {};
    // }

    std::array<uint16_t, 4> result{};

    // Oversample ADC inputs to get rid of ADC noise
    // std::array<uint32_t, 4> values{};

    for (int i = 0; i < 4; i++) {
        adc_select_input(i);
        result.at(i) = adc_read();
    }

    // for (uint8_t sample_number = 0; sample_number < m_config.sample_count; ++sample_number) {
    //     for (size_t idx = 0; idx < values.size(); ++idx) {
    //         adc_select_input(idx);
    //         values.at(idx) += adc_read();
    //     }
    // }

    // // Take average of all samples
    // std::ranges::transform(values, result.begin(), [&](const auto &sample) { return sample / m_config.sample_count;
    // });

    return result;
}

Drum::ExternalAdc::ExternalAdc(const Config::ExternalAdc &config) {
    // Enable level shifter
    gpio_init(config.spi_level_shifter_enable_pin);
    gpio_set_dir(config.spi_level_shifter_enable_pin, (bool)GPIO_OUT);
    gpio_put(config.spi_level_shifter_enable_pin, true);

    // Set up SPI
    gpio_set_function(config.spi_miso_pin, GPIO_FUNC_SPI);
    gpio_set_function(config.spi_mosi_pin, GPIO_FUNC_SPI);
    gpio_set_function(config.spi_sclk_pin, GPIO_FUNC_SPI);
    spi_init(config.spi_block, config.spi_speed_hz);

    gpio_init(config.spi_scsn_pin);
    gpio_set_dir(config.spi_scsn_pin, (bool)GPIO_OUT);

    Mcp3204Dma::run(config.spi_block, config.spi_scsn_pin);
}

std::array<uint16_t, 4> Drum::ExternalAdc::read() { return Mcp3204Dma::take_maximums(); }

Drum::Pad::Pad(const uint8_t channel) : m_channel(channel) {}

void Drum::Pad::setState(const bool state, const uint16_t debounce_delay) {
    if (m_active == state) {
        return;
    }

    // Immediately change the input state, but only allow a change every debounce_delay milliseconds.
    const uint32_t now = to_ms_since_boot(get_absolute_time());
    if (m_last_change + debounce_delay <= now) {
        m_active = state;
        m_last_change = now;
    }
}

void Drum::Pad::trigger(const uint16_t key_timeout) {
    const uint32_t now = to_ms_since_boot(get_absolute_time());

    // Respect per-pad debounce
    if (m_last_change + key_timeout > now) {
        return; // Too soon since last state change
    }

    m_active = true;
    m_last_trigger = now;
    m_last_change = now;
}

void Drum::Pad::updateTimeout(const uint16_t key_timeout) {

    if (!m_active) {
        return; // Not currently pressed
    }

    const uint32_t now = to_ms_since_boot(get_absolute_time());

    // Check if key timeout has expired
    if (now - m_last_trigger > key_timeout) {
        m_active = false;
        m_last_change = now;
    }
}

uint16_t Drum::Pad::getAnalog() {
    const auto raw_to_uint16 = [](uint16_t raw) { return ((raw << 4) & 0xFFF0) | ((raw >> 8) & 0x000F); };

    return raw_to_uint16(std::ranges::max_element(m_analog_buffer, [](const auto &a, const auto &b) {
                             return a.value < b.value;
                         })->value);
}

void Drum::Pad::setAnalog(uint16_t value, uint16_t debounce_delay) {
    const uint32_t now = to_ms_since_boot(get_absolute_time());

    // Clear outdated values, i.e. anything older than debounce_delay to allow for convenient configuration.
    while (!m_analog_buffer.empty() && (m_analog_buffer.front().timestamp + debounce_delay) <= now) {
        m_analog_buffer.pop_front();
    }

    m_analog_buffer.push_back({value, now});
}

Drum::RollCounter::RollCounter(uint32_t timeout_ms) : m_timeout_ms(timeout_ms) {};

void Drum::RollCounter::update(Utils::InputState &input_state) {
    const uint32_t now = to_ms_since_boot(get_absolute_time());
    if ((now - m_last_hit_time) > m_timeout_ms) {
        if (m_current_roll > 1) {
            m_previous_roll = m_current_roll;
        }
        m_current_roll = 0;
    }

    if (input_state.drum.don_left.triggered && (m_previous_pad_state.don_left != input_state.drum.don_left.triggered)) {
        m_last_hit_time = now;
        m_current_roll++;
    }
    if (input_state.drum.don_right.triggered &&
        (m_previous_pad_state.don_right != input_state.drum.don_right.triggered)) {
        m_last_hit_time = now;
        m_current_roll++;
    }
    if (input_state.drum.ka_right.triggered && (m_previous_pad_state.ka_right != input_state.drum.ka_right.triggered)) {
        m_last_hit_time = now;
        m_current_roll++;
    }
    if (input_state.drum.ka_left.triggered && (m_previous_pad_state.ka_left != input_state.drum.ka_left.triggered)) {
        m_last_hit_time = now;
        m_current_roll++;
    }

    m_previous_pad_state.don_left = input_state.drum.don_left.triggered;
    m_previous_pad_state.don_right = input_state.drum.don_right.triggered;
    m_previous_pad_state.ka_left = input_state.drum.ka_left.triggered;
    m_previous_pad_state.ka_right = input_state.drum.ka_right.triggered;

    input_state.drum.current_roll = m_current_roll;
    input_state.drum.previous_roll = m_previous_roll;
}

Drum::Drum(const Config &config) : m_config(config), m_roll_counter(config.roll_counter_timeout_ms) {

    std::visit(
        [this](auto &&config) {
            using T = std::decay_t<decltype(config)>;

            if constexpr (std::is_same_v<T, Config::InternalAdc>) {
                m_adc = std::make_unique<InternalAdc>(config);
            } else if constexpr (std::is_same_v<T, Config::ExternalAdc>) {
                m_adc = std::make_unique<ExternalAdc>(config);
            } else {
                static_assert(false, "Unknown ADC type!");
            }
        },
        m_config.adc_config);

    m_pads.emplace(Id::DON_RIGHT, config.adc_channels.don_right);
    m_pads.emplace(Id::DON_LEFT, config.adc_channels.don_left);
    m_pads.emplace(Id::KA_LEFT, config.adc_channels.ka_left);
    m_pads.emplace(Id::KA_RIGHT, config.adc_channels.ka_right);
}

std::map<Drum::Id, int32_t> Drum::readInputs() {
    std::map<Id, int32_t> result;

    const auto adc_values = m_adc->read();

    for (const auto &[id, pad] : m_pads) {
        result[id] = static_cast<int32_t>(adc_values.at(pad.getChannel()));
    }

    return result;
}

bool Drum::isGlobalDebounceElapsed() const {
    const uint32_t now = to_ms_since_boot(get_absolute_time());
    return (now - m_global_debounce_time) >= m_config.don_debounce;
}

void Drum::updateGlobalDebounce() { m_global_debounce_time = to_ms_since_boot(get_absolute_time()); }

uint16_t Drum::getThreshold(const Id pad_id, const Config::Thresholds &thresholds) const {
    switch (pad_id) {
    case Id::DON_LEFT:
        return thresholds.don_left;
    case Id::DON_RIGHT:
        return thresholds.don_right;
    case Id::KA_LEFT:
        return thresholds.ka_left;
    case Id::KA_RIGHT:
        return thresholds.ka_right;
    }
    assert(false);
    return 0;
}

void Drum::updateDigitalInputState(Utils::InputState &input_state, const std::map<Drum::Id, int32_t> &raw_values) {
    const uint32_t now = to_ms_since_boot(get_absolute_time());

    // PHASE 1: Maintain existing button states (key timeout logic)
    for (auto &[id, pad] : m_pads) {
        pad.updateTimeout(m_config.key_timeout_ms);
    }

    // Initialize weighted comparison state
    WeightedComparisonState wc_state{};

    // PHASE 2a: Collect Don candidates
    for (const auto &id : {Id::DON_LEFT, Id::DON_RIGHT}) {
        const auto &pad = m_pads.at(id);

        const int32_t adc_value = raw_values.at(id);
        const int32_t light_threshold = static_cast<int32_t>(getThreshold(id, m_config.trigger_thresholds));
        const int32_t last_adc_value = pad.getLastAdcValue();
        const int32_t delta = adc_value - last_adc_value;

        m_pads.at(id).setLastAdcValue(adc_value);

        if (pad.getState()) {
            continue;
        }

        // Check if above light threshold
        if (delta <= light_threshold) {
            continue;
        }

        // Per-sensor debounce check
        const uint32_t time_since_trigger = now - pad.getLastTrigger();
        if (time_since_trigger <= m_config.key_timeout_ms) {
            continue;
        }

        // Don pads: check same-type debounce AND crosstalk
        if (now - last_don_time < m_config.don_debounce || now - last_kat_time <= m_config.crosstalk_debounce) {
            continue;
        }

        // Mark as candidate instead of triggering immediately
        const float ratio = calculateTriggerRatio(delta, light_threshold);

        if (id == Id::DON_LEFT) {
            wc_state.don_left_candidate = true;
            wc_state.don_left_ratio = ratio;
        } else {
            wc_state.don_right_candidate = true;
            wc_state.don_right_ratio = ratio;
        }
    }

    // PHASE 2b: Collect Ka candidates
    for (const auto &id : {Id::KA_LEFT, Id::KA_RIGHT}) {
        const auto &pad = m_pads.at(id);

        const int32_t adc_value = raw_values.at(id);
        const int32_t light_threshold = static_cast<int32_t>(getThreshold(id, m_config.trigger_thresholds));
        const int32_t last_adc_value = pad.getLastAdcValue();
        const int32_t delta = adc_value - last_adc_value;

        m_pads.at(id).setLastAdcValue(adc_value);

        if (pad.getState()) {
            continue;
        }

        // Check if above light threshold
        if (delta <= light_threshold) {
            continue;
        }

        // Per-sensor debounce check
        const uint32_t time_since_trigger = now - pad.getLastTrigger();
        if (time_since_trigger <= m_config.key_timeout_ms) {
            continue;
        }

        // Ka pads: check same-type debounce AND crosstalk
        if (now - last_kat_time < m_config.kat_debounce || now - last_don_time <= m_config.crosstalk_debounce) {
            continue;
        }

        // PRIORITY CHECK: If ANY Don candidate exists, suppress all Ka
        if (wc_state.don_left_candidate || wc_state.don_right_candidate) {
            continue;
        }

        // Mark as candidate instead of triggering immediately
        const float ratio = calculateTriggerRatio(delta, light_threshold);

        if (id == Id::KA_LEFT) {
            wc_state.ka_left_candidate = true;
            wc_state.ka_left_ratio = ratio;
        } else {
            wc_state.ka_right_candidate = true;
            wc_state.ka_right_ratio = ratio;
        }
    }

    // PHASE 3: Apply weighted comparison (only if enabled)
    if (m_config.weighted_comparison_mode == Config::WeightedComparisonMode::On) {
        applyWeightedComparison(wc_state);
    }

    // PHASE 4: Trigger surviving candidates
    if (wc_state.don_left_candidate) {
        m_pads.at(Id::DON_LEFT).trigger(m_config.key_timeout_ms);
        last_don_time = now;
    }
    if (wc_state.don_right_candidate) {
        m_pads.at(Id::DON_RIGHT).trigger(m_config.key_timeout_ms);
        last_don_time = now;
    }
    if (wc_state.ka_left_candidate) {
        m_pads.at(Id::KA_LEFT).trigger(m_config.key_timeout_ms);
        last_kat_time = now;
    }
    if (wc_state.ka_right_candidate) {
        m_pads.at(Id::KA_RIGHT).trigger(m_config.key_timeout_ms);
        last_kat_time = now;
    }

    // PHASE 5: Output to InputState
    input_state.drum.don_left.triggered = m_pads.at(Id::DON_LEFT).getState();
    input_state.drum.ka_left.triggered = m_pads.at(Id::KA_LEFT).getState();
    input_state.drum.don_right.triggered = m_pads.at(Id::DON_RIGHT).getState();
    input_state.drum.ka_right.triggered = m_pads.at(Id::KA_RIGHT).getState();

    // PHASE 6: Update roll counter
    m_roll_counter.update(input_state);
}

void Drum::updateAnalogInputState(Utils::InputState &input_state, const std::map<Drum::Id, int32_t> &raw_values) {
    for (const auto &[id, raw] : raw_values) {
        m_pads.at(id).setAnalog(static_cast<uint16_t>(raw), m_config.debounce_delay_ms);

        switch (id) {
        case Id::DON_LEFT:
            input_state.drum.don_left.analog = m_pads.at(id).getAnalog();
            break;
        case Id::DON_RIGHT:
            input_state.drum.don_right.analog = m_pads.at(id).getAnalog();
            break;
        case Id::KA_LEFT:
            input_state.drum.ka_left.analog = m_pads.at(id).getAnalog();
            break;
        case Id::KA_RIGHT:
            input_state.drum.ka_right.analog = m_pads.at(id).getAnalog();
            break;
        }
    };
}

void Drum::updateInputState(Utils::InputState &input_state) {
    const auto raw_values = readInputs();

    input_state.drum.don_left.raw = static_cast<uint16_t>(raw_values.at(Id::DON_LEFT));
    input_state.drum.don_right.raw = static_cast<uint16_t>(raw_values.at(Id::DON_RIGHT));
    input_state.drum.ka_left.raw = static_cast<uint16_t>(raw_values.at(Id::KA_LEFT));
    input_state.drum.ka_right.raw = static_cast<uint16_t>(raw_values.at(Id::KA_RIGHT));

    updateDigitalInputState(input_state, raw_values);
    updateAnalogInputState(input_state, raw_values);
}

void Drum::setDebounceDelay(const uint16_t delay) { m_config.debounce_delay_ms = delay; }

void Drum::setDonDebounceMs(const uint16_t ms) { m_config.don_debounce = ms; }

void Drum::setKatDebounceMs(const uint16_t ms) { m_config.kat_debounce = ms; }

void Drum::setCrosstalkDebounceMs(const uint16_t ms) { m_config.crosstalk_debounce = ms; }

void Drum::setKeyTimeoutMs(const uint16_t ms) { m_config.key_timeout_ms = ms; }

void Drum::setTriggerThresholds(const Config::Thresholds &thresholds) { m_config.trigger_thresholds = thresholds; }

void Drum::setDoubleTriggerMode(const Config::DoubleTriggerMode mode) { m_config.double_trigger_mode = mode; }

void Drum::setDoubleThresholds(const Config::Thresholds &thresholds) {
    m_config.double_trigger_thresholds = thresholds;
}

void Drum::setWeightedComparisonMode(const Config::WeightedComparisonMode mode) {
    m_config.weighted_comparison_mode = mode;
}

float Drum::calculateTriggerRatio(const int32_t delta, const uint16_t threshold) const {
    if (threshold == 0) {
        return 0.0f;
    }
    return static_cast<float>(delta) / static_cast<float>(threshold);
}

void Drum::applyWeightedComparison(WeightedComparisonState &state) {
    // constexpr float EPSILON = 0.01f; // 1% tie threshold

    // Compare Don pair (only if BOTH candidates)
    if (state.don_left_candidate && state.don_right_candidate) {
        // if (std::abs(state.don_left_ratio - state.don_right_ratio) > EPSILON) {
        if (state.don_left_ratio > state.don_right_ratio) {
            state.don_right_candidate = false;
        } else {
            state.don_left_candidate = false;
        }
        //}
        // If within epsilon, both remain candidates
    }

    // Compare Ka pair (only if BOTH candidates)
    if (state.ka_left_candidate && state.ka_right_candidate) {
        // if (std::abs(state.ka_left_ratio - state.ka_right_ratio) > EPSILON) {
        if (state.ka_left_ratio > state.ka_right_ratio) {
            state.ka_right_candidate = false;
        } else {
            state.ka_left_candidate = false;
        }
        //}
        // If within epsilon, both remain candidates
    }
}

} // namespace Doncon::Peripherals