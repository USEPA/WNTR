# Affected-Node Identification & Ranking Rules (`TASK-07`)

# note: I used gemini to help generate the syntax for these rules, these are references for calculations done

## 1. Architecture Requirement & Unit Conversion

- **Architecture Requirement:** Consumer junctions must maintain pressure at or above **$20.0\text{ psi}$**. Any node with pressure strictly below $20.0\text{ psi}$ ($P < 20.0\text{ psi}$) is in a low-pressure violation state.
- **WNTR Unit Conversion:** WNTR hydraulic simulations output node pressure in **meters of water head ($\text{m}$)**. Assuming fresh water at standard density ($\text{SG} = 1.0$, $g = 9.80665\text{ m/s}^2$):
  - $1\text{ m H}_2\text{O} = 1.4223343\text{ psi}$
  - $1\text{ psi} = 0.7030696\text{ m H}_2\text{O}$
  - **$20.0\text{ psi}$ Threshold in Meters:** $20.0 \times 0.7030696 = \mathbf{14.06139\text{ m}}$
- **Deviations:** None from the $20.0\text{ psi}$ architecture minimum. Additional degradation and water-service delivery thresholds below are introduced as **provisional demo rules** awaiting sponsor confirmation.

---

## 2. Agreed Demo Rules & Thresholds

| Rule / Parameter | Value & Units | Status | Purpose |
| :--- | :--- | :--- | :--- |
| **Minimum Pressure Threshold** | `< 20.0 psi` (`< 14.061 m`) | **Approved (Architecture)** | Flags critical low pressure. Pressures strictly at `20.0 psi` are compliant. |
| **Significant Pressure Drop Threshold** | `>= 5.0 psi` (`>= 3.515 m`) | **PROVISIONAL — Awaiting Sponsor Confirmation** | Flags severe attack-induced pressure loss even if pressure stays `>= 20.0 psi`, and determines whether pre-existing low pressure was worsened by the attack. |
| **Water-Service Delivery Ratio** | `< 0.95` (`< 95%` of baseline demand) | **PROVISIONAL — Awaiting Sponsor Confirmation** | Flags nodes where delivered demand falls below 95% of baseline demand during timesteps with positive baseline demand. |
| **Summarized Time Period** | Outage window `(start_time_sec, end_time_sec]` | **PROVISIONAL — Awaiting Sponsor Confirmation** | Summarizes active outage timesteps (e.g., `3600 s` to `10800 s` / Hours `1.0`–`3.0` for `pump_poweroff_basic.json`). |
| **Primary Ranking Measure** | `max_pressure_drop_psi` (descending) | **Approved for Demo** | Ranks the node experiencing the largest peak pressure drop (`baseline - attack`) as `#1`. |
| **Equal-Ranking Tie-Breaker** | 1. `max_pressure_drop_psi` (desc)<br>2. `duration_hours` (desc)<br>3. `attack_min_pressure_psi` (asc)<br>4. `node_id` (asc) | **Approved for Demo** | Guarantees deterministic ordering (`rank = 1, 2, 3, ...`) when two or more nodes have identical pressure drops. |

---

## 3. Distinguishing Pre-Existing Issues vs. Attack-Caused Impacts

1. **`attack_induced_low_pressure`:** Baseline pressure stayed $\ge 20.0\text{ psi}$ throughout the window, and attack pressure dropped $< 20.0\text{ psi}$.
2. **`worsened_pre_existing_low_pressure`:** Node was already $< 20.0\text{ psi}$ in the baseline simulation, **and** the attack caused an additional drop $\ge 5.0\text{ psi}$ or reduced demand delivery below $95\%$.
3. **`attack_induced_degradation`:** Pressure remained $\ge 20.0\text{ psi}$, but dropped by $\ge 5.0\text{ psi}$ or suffered a $< 95\%$ demand delivery shortfall.
4. **`pre_existing_low_pressure_unchanged` (Excluded from `affected_nodes`):** Node was already $< 20.0\text{ psi}$ in baseline and experienced $< 5.0\text{ psi}$ additional drop and $\ge 95\%$ demand delivery. Returned separately under `pre_existing_only_nodes` so baseline network deficiencies are not misattributed to the cyber attack.

---

## 4. Hand-Checked Dataset Verification

Tested in `tests/test_analysis.py::test_hand_checked_thresholds_below_at_and_above` over a 2-hour outage window (`t = 7200 s` and `t = 10800 s`, `1.0 hr` per step):

| Test Node | Baseline Pressure ($\text{psi}$) | Attack Pressure ($\text{psi}$) | Max Drop ($\text{psi}$) | Boundary Tested | Expected Classification | Rank |
| :--- | :---: | :---: | :---: | :--- | :--- | :---: |
| `N_below` | `30.0` | `19.9` (2 hrs) | `10.1` | Strictly **below** `20.0 psi` | Affected (`attack_induced_low_pressure`) | `1` |
| `N_pre_worsened` | `18.0` | `12.0` (2 hrs) | `6.0` | Pre-existing `< 20 psi` + drop `>= 5.0 psi` | Affected (`worsened_pre_existing_low_pressure`) | `2` |
| `N_drop_exact` | `30.0` | `25.0` (1 hr), `30.0` (1 hr) | `5.0` | Strictly **at** `5.0 psi` drop limit | Affected (`attack_induced_degradation`) | `3` |
| `N_at` | `24.9` | `20.0` (2 hrs) | `4.9` | Strictly **at** `20.0 psi` (drop `< 5.0`) | Not affected (compliant) | — |
| `N_above` | `25.0` | `20.1` (2 hrs) | `4.9` | Strictly **above** `20.0 psi` | Not affected (compliant) | — |
| `N_pre_unchanged` | `18.0` | `17.5` (2 hrs) | `0.5` | Pre-existing `< 20 psi`, drop `< 5.0` | Isolated in `pre_existing_only_nodes` | — |

---

## 5. Decision & Sign-Off Record

- **Decision:** Approve the affected-node rules, `20.0 psi` (`14.06139 m`) architecture conversion, pre-existing vs. attack-induced separation, and deterministic ranking/tie-breaking rules for use in the pump shutdown demo analysis.
- **Reviewer / Author:** Simon Zhao (`task-7`)
- **Date:** 2026-11-12
- **Sponsor Confirmation Still Needed:**
  1. Confirm provisional `5.0 psi` significant pressure drop threshold.
  2. Confirm provisional `95%` (`0.95`) minimum water-service demand delivery ratio.
  3. Confirm whether post-outage recovery timesteps should be included in the summarized window or kept strictly to the active outage window `(start_time_sec, end_time_sec]`.