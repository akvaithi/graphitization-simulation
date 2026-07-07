# Sources

Every mechanism and scale-up assumption in this simulation is backed by a
citation here, so claims can be defended from the literature rather than from the
model's math. Organized by the part of the process each supports. Where a claim
is a *hypothesis-level* modeling choice (no data yet), it is marked **[modeling
assumption]** and the citation is the closest supporting precedent, not proof.

---

## 1. The process (this group)

- **Banavath, R.; Zhang, Y.; Deshpande, S.; Lutkenhaus, J. L.; Green, M. J.**
  "Low-temperature catalytic upcycling of petroleum coke into battery-grade
  graphite." *npj Materials Sustainability* **4**:23 (2026). Open access.
  <https://www.nature.com/articles/s44296-026-00115-w> — the pre-additive
  Fe-catalyzed route (PC:Fe 1:1, ≤1600 °C); Fe loading plateaus ~50 wt%; bigger
  pellets (1.2→7 g) lowered DG 97.7→94.1%; recoverable Fe catalyst.
- **AIChE Annual Meeting 2025 (paper 693e):** "Development of a Catalytic
  Graphitization Process for Battery-Grade Graphite Synthesis from Fuel-Grade Pet
  Coke." <https://proceedings.aiche.org/conferences/aiche-annual-meeting/2025/proceeding/paper/development-catalytic>
  — the fuel-grade (high-sulfur) extension this project builds on.
- Pending patent **63/704,517** (TAMU; Banavath & Green) — the CaCO₃-additive system.

## 2. Fe-catalyzed graphitization mechanism (dissolution–reprecipitation)

- **Iron-catalyzed graphitization of isotropic carbon**, *Carbon* **21** (1983)
  <https://www.sciencedirect.com/science/article/abs/pii/0008622383901604> — the
  classic HRTEM evidence for Fe carbide → metallic Fe → graphite; dissolution and
  reprecipitation of ordered layers at the Fe interface.
- **Li, H. et al.**, *Fuel* **279** (2020) 118531 — iron catalytic graphitization
  of coke carbon: mechanism, morphology, lattice fringes.
- **Frankenstein, L. et al.**, *ChemElectroChem* (2023)
  <https://chemistry-europe.onlinelibrary.wiley.com/doi/10.1002/celc.202201073> —
  different iron precursors for catalytic graphitization of LIB anode carbon;
  carbide forms then decomposes to metallic Fe + graphite below ~1000 °C.
- **Fe-based catalysts for petroleum-coke graphitization for LIB**, *Mater. Lett.*
  (2021) <https://www.sciencedirect.com/science/article/abs/pii/S0167577X21012544>.
- Supports the model's **Langmuir Fe-fraction saturation** (plateau ~50 wt% Fe)
  and the **ordering coordinate Q** driving peak sharpening/position.

## 3. H1 — sulfur trapping by CaO (confirmed in this project)

- **Poisoning of iron catalyst by sulfur**, *Appl. Catal. A* (2007)
  <https://www.sciencedirect.com/science/article/abs/pii/S0920586107001022> — H₂S
  strongly retards graphite deposition on iron during high-temperature
  carburization: the mechanistic basis for sulfur poisoning of the Fe catalyst,
  which is why the high-sulfur (~7 wt%) green coke needs sulfur control.
- **Majumder et al.**, *Environmental Protection Research* **3**(2) (2023) 341–348
  <https://ojs.wiserpub.com/index.php/EPR/article/view/2992> — ~10 wt% CaO is most
  effective for trapping free sulfur in petroleum coke (67% SO₂ reduction on
  combustion); the CaO + S sulfur-capture basis.
- **Reduced-iron-powder catalytic roasting desulfurization of high-sulfur pet
  coke**, *J. Environ. Chem. Eng.* (2024)
  <https://www.sciencedirect.com/science/article/abs/pii/S2213343724029920> —
  Fe powder + 1400 °C/1 h gave 87.9% desulfurization to 0.91 wt% S; couples
  desulfurization to graphitization performance.
- **Deep desulfurization of high-sulfur pet coke** (alkali roasting), *ACS Omega*
  (2024) <https://pmc.ncbi.nlm.nih.gov/articles/PMC11173515/> — alkaline roasting
  route, 700 °C / 2 h; context for the calcination-temperature window.
- **Oxidation of CaS at fluidised-bed temperatures**, *Combust. Flame*
  <https://www.sciencedirect.com/science/article/abs/pii/S0082078406806466> —
  CaS ↔ CaSO₄ speciation: under inert Ar the product is **CaS**; with O₂ present
  it can shift toward CaSO₄, and at very high T sulfur can re-evolve. Backs the
  model booking CaS under argon and the O₂ caveat.

## 4. H2 — Boudouard etching (CO₂ gasifies reactive/amorphous carbon)

- **Guo, W. et al.**, "Boudouard reaction accompanied by graphitization of
  wrinkled carbon layers in coke gasification," *Fuel* **298** (2021) 120730
  <https://www.sciencedirect.com/science/article/pii/S0016236121006244> — CO₂
  gasification (C + CO₂ → 2 CO) simultaneously etches carbon and orders the
  remaining layers.
- **Reverse-Boudouard reactivity of amorphous carbon** (defects/ID:IG), *Gases*
  (2025) <https://doi.org/10.3390/gases6020023> — amorphous, high-ID/IG carbon has
  a high density of reactive sites and gasifies preferentially over ordered
  carbon; basis for the model's amorphous-selective etch (`alpha_H2`).
- **Boudouard reaction overview**, *ScienceDirect Topics*
  <https://www.sciencedirect.com/topics/engineering/boudouard-reaction> — the
  reaction becomes significant >700 °C.

## 5. Scale-up: rotary kiln, residence time, atmosphere

- **Sunkara et al.**, "Residence time and mass flow rate of particles in carbon
  rotary kilns," *Powder Technol.* (2009)
  <https://www.sciencedirect.com/science/article/abs/pii/S0255270109000063> —
  residence-time distribution in carbon rotary kilns; basis for the kiln's
  short, hold-free thermal history. **[modeling assumption]** for the triangular
  ramp/cool profile.
- **Petroleum-coke calcining practice** (industry): calcining runs **1150–1350 °C**
  in an **oxygen-deficient (not fully inert)** atmosphere; three steps drying →
  devolatilization → densification.
  <https://kintekfurnace.com/faqs/what-is-the-primary-function-of-a-rotary-kiln-in-the-petroleum-coke-calcination-process>
  — supports both the kiln temperature ceiling and the **O₂-ingress** knob.
- **Experimental investigation of process parameters during graphitization of
  catalytic coke**, *Int. J. Coal Sci. Technol.* (2019)
  <https://link.springer.com/article/10.1007/s40789-019-00279-y> — metal-catalyzed
  coke graphitization above ~800 °C; catalyst effectiveness order Ni > Mn > Fe.

## 6. Scale-up: Fe–carbon binding method (pellet / wet impregnation / extrusion)

- **Wet impregnation** — Frankenstein 2023 (§2) and **Fe-impregnated biochar
  graphitization** <https://www.diva-portal.org/smash/get/diva2:1575627/FULLTEXT03.pdf>
  — solution-deposited Fe salts (Fe(NO₃)₃, FeCl₃) give more homogeneous dispersion
  and better carbon contact; loading, time, and temperature all raise DG.
  **[modeling assumption]** for `wet_impregnation` having the highest contact factor.
- **Impregnation catalyst preparation** review, *Catal. Rev.* (1985)
  <https://www.tandfonline.com/doi/abs/10.1080/01614948508064738> — incipient-
  wetness fundamentals and dispersion control.
- **Extrusion / pressureless shaping** — FEECO, "Catalyst Pelletizing"
  <https://feeco.com/catalyst-pelletizing-for-enhanced-performance-and-longevity/>
  (pelletizing/granulation is a *non-pressure* forming route, unlike pressing);
  and **solvent-free graphite anode by PTFE/PVDF**, *Energy Technol.* (2022)
  <https://onlinelibrary.wiley.com/doi/full/10.1002/ente.202200732> — binder-based
  shaping without high compaction pressure. **[modeling assumption]** for
  `extrusion` (good mixing, lower pressure than a pressed pellet) and `dry_mix`
  (loose powder, poorest contact).

## 7. XRD method & amorphous quantification (the DG%-vs-amount gap)

- **Maire, J. & Méring, J.**, *Chem. Phys. Carbon* **6** (1970) 125–190 — the DG%
  (degree-of-graphitization) d-spacing relation.
- **Iwashita, N. et al.**, *Carbon* **42** (2004) 701–714 — standard XRD procedure
  for carbon (windowing, background, profile fitting).
- **Lu, L.; Sahajwalla, V.; Kong, C.; Harris, D.**, *Carbon* **39** (2001)
  1821–1833 — deconvolving the (002) band into crystalline + amorphous components
  (the crystallinity-index basis) and the TGA differential-oxidation split.
- **Ruland, W. & Smarsly, B.**, *J. Appl. Cryst.* **35** (2002) 624 — why a peak-
  area ratio is a **model-dependent index, not a mass fraction** (needs physical
  standards); the reason calibration is required.
- **Franklin, R. E.**, *Proc. R. Soc. A* **209** (1951) 196; **Warren, B. E.**,
  *Phys. Rev.* **59** (1941) 693 — turbostratic vs graphitic stacking; d₀₀₂ and Lc.

---

### How the model maps to these

| Model element (sim/) | Backed by |
|---|---|
| Fe Langmuir saturation, ordering coordinate | §2 |
| Multi-segment tube program, preheat holds | group's C01..T10 program (this file's furnace notes) |
| Rotary-kiln hold-free triangle, 1300 °C/2 h | §5 (Sunkara; calcining practice) **[modeling assumption]** |
| H1 sulfur poisoning + CaO→CaS trapping | §3 |
| H2 Boudouard amorphous-selective etch | §4 |
| O₂ combustion term (non-inert atmosphere) | §5 (oxygen-deficient calcining); §3 (CaSO₄ shift) |
| Binding-method contact factor | §6 **[modeling assumption]** |
| Crystallinity index, calibration, DG% caveat | §7 |
