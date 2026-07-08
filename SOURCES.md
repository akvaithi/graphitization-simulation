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

## 2b. H3 — calcium dispersion, wetting, and co-catalysis (the focus mechanism)

H2 (Boudouard) has negligible impact in the fit, so H3 is the discrimination focus.
Calcium acts through several routes, all literature-supported:

- **Ca is itself a graphitization catalyst.** "The mechanisms of calcium-catalyzed
  graphenization of cellulose and lignin biochars," *Sci. Rep.* **13** (2023)
  <https://www.nature.com/articles/s41598-023-38433-x> — CaO + amorphous C -> a
  metastable **CaC₂** that decomposes to a graphenic shell; well-ordered graphene
  forms above ~1200 °C, far below the >2000 °C non-catalytic route. A basis for the
  observed onset shift to lower temperature.
- **Calcium as an effective, cheap graphitization catalyst.** *Sci. Rep.* **12**
  (2022) <https://www.nature.com/articles/s41598-022-25943-3> — calcium is cheap,
  non-toxic, and catalyzes graphene-like material formation from cellulose.
- **Ca disperses the metal catalyst and prevents sintering.** "Effect of Ca
  Promoter on the Structure, Performance, and Carbon Deposition of Ni-Al₂O₃,"
  *ACS Omega* (2020) <https://pubs.acs.org/doi/10.1021/acsomega.0c02558> — CaO
  reduces metal particle size (confinement effect) and improves anti-sintering.
- **Ca wets the iron surface.** "Application of TOF-SIMS in the Study of Wetting
  the Iron(111) Surface with Promoter Oxides," *Materials* (2022)
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC8840287/> — calcium wets/spreads on
  iron, forming a CaO-FeₓOy layer — the wetting basis for improved Fe-carbon
  contact. Lattice-integrated Ca favors graphitic carbon; excess Ca over-
  graphitizes (implying an optimum loading), consistent with the observed
  CaCO₃ threshold and saturation.

The model lumps these into a saturating rate multiplier `disp = 1 + h3_gain·u/(u+u½)`
in the CaO fraction — dispersion + wetting + co-catalysis together. **[modeling
assumption]** for the exact functional form.

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

## 5. Scale-up: rotary-kiln hold, heat transfer, industry solutions

- **Rotary-kiln temperature zones** (Kintek): the kiln does not apply a single
  temperature — material is **heated, held at peak for a residence time, then
  cooled**, all in one machine.
  <https://kintekfurnace.com/faqs/what-are-the-zones-inside-the-rotary-kiln-cylinder>
  — the basis for modeling the kiln WITH an isothermal hot-zone hold (correcting
  the earlier hold-free triangle).
- **Sunkara et al.**, "Residence time and mass flow rate of particles in carbon
  rotary kilns," *Powder Technol.* (2009)
  <https://www.sciencedirect.com/science/article/abs/pii/S0255270109000063> —
  residence-time behavior in carbon rotary kilns.
- **Carbon heat transfer** — "Thermo-Physical Properties of Petroleum Coke during
  Calcining/Graphitization," *Springer* (2016)
  <https://link.springer.com/content/pdf/10.1007/978-3-319-48245-3_24.pdf> — raw
  coke thermal conductivity rises from ~2.0 to ~4.2 W/m·K to 1000 °C, increasing
  with graphitization. Low enough that a thick cross-section lags, high enough
  that a thin puck (Bi ≈ 0.07) equilibrates in under a minute — the basis for the
  lumped-capacitance thermal lag keyed to the **cross-section** (L²/α), which the
  **extruder** route holds constant. **[modeling assumption]** for the τ = τ_lin·L
  + τ_quad·L² form.
- **Pet-coke calcining practice**: **1150–1350 °C**, **oxygen-deficient** (not
  fully inert) atmosphere.
  <https://kintekfurnace.com/faqs/what-is-the-primary-function-of-a-rotary-kiln-in-the-petroleum-coke-calcination-process>
  — supports the kiln temperature ceiling and the O₂-ingress knob.
- **Industrial graphitization equipment / scale-up** (QF Industrial): the field
  runs batch **Acheson** furnaces (2800–3000 °C, ~4000–4800 kWh/t) and is moving
  to **continuous graphitization furnaces** (24 h, single-line to ~10,000 t/yr),
  with **microwave/plasma** emerging.
  <https://www.qfindustrial.com/news/graphitization-is-a-core-step-in-the-production-process-in-what-equipment-is-it-usually-carried-out/>
  — context for where a low-temperature catalytic rotary-kiln route sits, and why
  continuous/extruded processing is the scale path.
- **Experimental investigation of process parameters during graphitization of
  catalytic coke**, *Int. J. Coal Sci. Technol.* (2019)
  <https://link.springer.com/article/10.1007/s40789-019-00279-y> — metal-catalyzed
  coke graphitization above ~800 °C; catalyst effectiveness Ni > Mn > Fe.

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
| Rotary-kiln isothermal hot-zone hold, 1300 °C/2 h | §5 (Kintek zones; Sunkara) |
| Lumped-capacitance thermal lag keyed to cross-section | §5 (coke k; extruder route) **[modeling assumption]** |
| H1 sulfur poisoning + CaO→CaS trapping | §3 |
| **H3 Ca dispersion + wetting + CaC₂ co-catalysis (focus)** | §2b |
| H2 Boudouard etch (negligible in the fit) | §4 |
| O₂ combustion term (non-inert atmosphere) | §5 (oxygen-deficient calcining); §3 (CaSO₄ shift) |
| Binding-method contact factor | §6 **[modeling assumption]** |
| Crystallinity index, calibration, DG% caveat | §7 |
