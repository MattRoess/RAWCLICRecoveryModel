# BEV Traction Motor Recycling: Process Routes, NdFeB Recovery, and Transfer Coefficients — A Literature Review for 2030 and 2060

*RAWCLIC Project / EMPA — September 2026*

EU Project 101183654

## 1 Executive Summary

This literature review assesses end-of-life recycling routes for battery-electric-vehicle traction motors, with particular emphasis on neodymium–iron–boron permanent magnets, the rare-earth elements neodymium, praseodymium, dysprosium and terbium, and the transfer coefficients needed for prospective material-flow modelling in 2030 and 2060.

The scope begins when the traction-motor unit is removed from the vehicle. Vehicle collection, depollution and motor removal are retained in the transfer-coefficient chain because they determine how much material reaches the defined motor-unit boundary, but detailed vehicle-treatment operations upstream of motor removal are not modelled. The physical foreground system covers dehousing, rotor–stator separation, demagnetisation, magnet extraction or shredding, magnet recycling, rare-earth separation and purification, and production of rare-earth oxide or metal. Copper, aluminium and electrical steel are addressed as associated motor materials.

A nominal 150 kW radial permanent-magnet synchronous motor is represented by a planning allowance of 1.0 | 1.5 | 2.0 kg of NdFeB magnets. Within that magnet mass, the corresponding bounded elemental allowances are 0.25 | 0.38 | 0.55 kg Nd, 0.03 | 0.08 | 0.15 kg Pr, 0.01 | 0.05 | 0.12 kg Dy and 0.00 | 0.01 | 0.03 kg Tb. These are engineering planning ranges rather than an independently weighed bill of materials for a particular production motor [1] [2]. The same reference motor contains approximately 8 | 11 | 14 kg copper, 8 | 12 | 17 kg aluminium and 28 | 37 | 46 kg electrical steel in the stator and rotor laminations [1] [2]. RAWCLIC’s consolidated dataset separately models permanent-magnet, induction and electrically excited synchronous motors and reports material composition at vehicle level, reflecting the fact that vehicles can contain more than one traction motor [3] [4].

Only PMSMs and permanent-magnet axial-flux machines are the primary focus of magnet recycling. Asynchronous or induction machines and electrically excited synchronous machines are magnet-free in the relevant sense: they do not contain NdFeB traction magnets. They remain important sources of copper, aluminium and electrical steel, and EESMs may contain additional rotor copper, but they do not provide an NdFeB feedstock [1] [2]. Axial flux is a geometric category rather than a magnet chemistry; the axial-flux machines considered here generally use permanent magnets and therefore enter the magnet-recycling system.

A transfer coefficient, or TC, is defined in this review exactly as the fraction of a material entering a process that exits that process in the desired or recoverable output. The denominator and desired output must therefore be stated. A magnet-extraction TC, for example, is not interchangeable with a rare-earth leaching yield, product purity, recycling-content target or vehicle collection rate.

The principal findings are as follows.

1. **The present system is not one uniform industrial route.** Legacy end-of-life-vehicle treatment is based on depollution, component removal where required or economically attractive, fragmentation and mechanical separation. Bulk ferrous and non-ferrous recovery is mature, but public evidence does not establish that every current EV traction motor is shredded, nor does it provide auditable fleet-wide shares for shredding, motor resale, remanufacturing, manual dismantling or specialist magnet recovery. Project and pilot systems already demonstrate selective and robot-assisted motor disassembly [[5]](https://joint-research-centre.ec.europa.eu/jrc-news-and-updates/innovative-requirements-could-boost-circular-economy-plastics-and-critical-raw-materials-vehicles-2023-07-13_en) [[6]](https://link.springer.com/chapter/10.1007/978-3-031-84744-8_6) [[7]](https://www.sciencedirect.com/science/article/pii/S2212827125003786) [[8]](https://www.fraunhofer.de/en/press/research-news/2024/january-2024/electromobility-second-life-for-electric-motors.html) [[9]](https://www.iwks.fraunhofer.de/en/competencies/zdr-emil.html).

2. **Shredding is effective for throughput but can destroy the concentration needed for magnet recycling.** NdFeB is brittle and ferromagnetic. Untreated magnets may fragment and report with ferrous material, non-ferrous concentrates or residues. Once diluted or attached to steel fragments, the rare-earth content can become technically or economically difficult to recover. This is value leakage, but the available evidence does not support assigning a universal near-zero recovery coefficient to all shredding routes [[10]](https://doi.org/10.1177/0734242x261476422) [[11]](https://pubmed.ncbi.nlm.nih.gov/42625283/) [[12]](https://chemrxiv.org/engage/chemrxiv/article-details/6721e7215a82cea2fa4debeb) [[13]](https://link.springer.com/article/10.1007/s12649-026-03754-1). Thermal demagnetisation followed by controlled shredding and screening has increased an NdFeB-rich fraction from approximately 9.47% to 50.8% by mass in a reported demonstration; concentration is not the same as recovery [[10]](https://doi.org/10.1177/0734242x261476422) [[11]](https://pubmed.ncbi.nlm.nih.gov/42625283/) [[12]](https://chemrxiv.org/engage/chemrxiv/article-details/6721e7215a82cea2fa4debeb).

3. **Selective disassembly is the enabling route for high-value magnet recovery.** The necessary depth is motor dehousing, rotor–stator separation and access to embedded or surface-mounted magnets. Adhesives, sleeves, bandages, coatings and interior rotor geometries complicate extraction. Manual dismantling is flexible but labour-intensive. Semi-automated and robotic cells are at pilot or demonstration status and require adaptable sensing, tooling and process planning because returned motors are heterogeneous [[14]](https://www.sciencedirect.com/science/article/pii/S0921344924001769) [[15]](https://link.springer.com/chapter/10.1007/978-3-031-47394-4_45) [[6]](https://link.springer.com/chapter/10.1007/978-3-031-84744-8_6) [[16]](https://www.sciencedirect.com/science/article/pii/S2214993725003549) [[7]](https://www.sciencedirect.com/science/article/pii/S2212827125003786) [[8]](https://www.fraunhofer.de/en/press/research-news/2024/january-2024/electromobility-second-life-for-electric-motors.html) [[9]](https://www.iwks.fraunhofer.de/en/competencies/zdr-emil.html).

4. **Direct reuse has the highest potential value retention but the narrowest acceptance window.** An intact magnet must satisfy dimensional, coating, corrosion, magnetic-property and traceability requirements. Publicly auditable yields for traction-motor magnet reuse are not reported in the compiled evidence. Direct reuse must not therefore be assigned an assumed high recovery rate.

5. **Hydrogen decrepitation and HPMS are the leading short-loop routes.** Hydrogen causes NdFeB to decrepitate into powder and can assist liberation from assemblies. The recovered alloy can be cleaned, blended, milled and consolidated into new magnets without first separating every rare-earth element. HPMS has progressed beyond laboratory work into pilot and early commercial deployment, including facilities associated with HyProMag; nevertheless, plant-wide mass balances from end-of-life traction motors to qualified new automotive magnets remain commercially sparse [[17]](https://www.sciencedirect.com/science/article/pii/S2214993725055123) [[18]](https://www.fastmarkets.com/insights/rare-earth-magnet-recycling-technology-branches-out/) [[19]](https://www.okonrecycling.com/magnet-recycling-and-applications/magnet-technology/rare-earth-motor-magnet-recycling/) [[20]](https://www.iwks.fraunhofer.de/en/competencies/MagneticMaterials/Recycling.html) [[21]](https://www.iwks.fraunhofer.de/en/projects/current-projects/recyper.html) [[9]](https://www.iwks.fraunhofer.de/en/competencies/zdr-emil.html) [[22]](https://rare-earth-mining.com/hypromag/) [[23]](https://hypromagusa.com/technology/) [[24]](https://hypromag.com/executive-summary-of-recent-technical-progress-by-hypromag-ltd-june-2025/) [[25]](https://hypromag.com/about/).

6. **HDDR is not simply another name for hydrogen decrepitation.** Hydrogenation–disproportionation–desorption–recombination changes the alloy microstructure and can produce fine, potentially anisotropic material. It is relevant to powder upgrading and bonded or reprocessed magnet routes, but public evidence does not establish it as the dominant current industrial treatment of complete end-of-life traction motors [[26]](https://pubs.acs.org/acsodf/article/8/20/17431/407376/Review-on-the-Parameters-of-Recycling-NdFeB) [[27]](https://pmc.ncbi.nlm.nih.gov/articles/PMC12897740/) [[28]](https://research.birmingham.ac.uk/en/publications/recycling-of-ndfeb-magnets-from-hard-disc-drive-scrap-using-hpms-/) [[29]](https://link.springer.com/article/10.1007/s10163-025-02162-2) [[30]](https://onlinelibrary.wiley.com/doi/10.1155/2014/638013).

7. **Hydrometallurgy is the most established long-loop option for producing purified rare-earth compounds.** Magnet material is dissolved or converted into a leachable phase; impurities are removed; rare earths are separated and precipitated or calcined. Individual studies and commercial claims report high extraction or recovery, including values exceeding 99% and a supplier claim of 99.8%. These values apply to specified chemical stages or prepared feedstocks, not to the full chain beginning with an end-of-life vehicle [[31]](https://www.mdpi.com/2227-9717/13/6/1729) [[32]](https://pubs.rsc.org/en/content/articlehtml/2025/cc/d4cc04252b) [[33]](https://www.okonrecycling.com/magnet-recycling-and-applications/magnet-technology/ev-motor-magnet-recovery/) [[34]](https://www.reecycleinc.com/recycle-electric-motor-magnets) [[19]](https://www.okonrecycling.com/magnet-recycling-and-applications/magnet-technology/rare-earth-motor-magnet-recycling/). Hydrometallurgy accommodates mixed or oxidised feed better than direct recycling, but consumes reagents and generates liquid and solid residues.

8. **Pyrometallurgy tolerates heterogeneous feed but usually requires a downstream chemical route.** High-temperature treatment can separate bulk metals and concentrate rare earths in a slag or alloy. One reported single-furnace approach achieved up to 91% neodymium extraction into a target phase using a fayalite flux [[31]](https://www.mdpi.com/2227-9717/13/6/1729). This is a process-stage result, not a complete motor-to-metal TC. Energy consumption is not consistently reported and is therefore marked NR rather than estimated.

9. **No evidence-supported full-chain TC exists for 2030 or 2060.** The literature provides selected laboratory yields, enrichment factors and commercial claims, but does not provide compatible, independently audited coefficients for capture, motor removal, dehousing, extraction, recycling, elemental separation and oxide/metal conversion. Consequently, this report does not manufacture a numerical full-chain forecast. Its 2030 and 2060 tables are explicitly labelled scenario-parameter frameworks; unsupported cells are NR.

10. **The likely 2030 main route is a portfolio, not one universal process.** Selective motor removal, semi-automated disassembly and short-loop hydrogen processing are likely to be preferred for known, clean NdFeB feed. Hydrometallurgy will remain necessary for mixed, oxidised or chemically incompatible material. Controlled shredding after demagnetisation may serve motors that cannot be economically dismantled.

11. **The 2060 result is a scenario, not a forecast.** A mature circular system would route reusable motors and magnets to reuse, composition-controlled magnets to short-loop recycling, and contaminated material to long-loop recovery. Its feasibility depends more on collection, identification, design for disassembly, product qualification and contractual feedstock control than on laboratory extraction yields alone.

12. **Regulation is an important driver but not evidence of achieved recovery.** Regulation (EU) 2024/1252, the Critical Raw Materials Act, is enacted and establishes strategic benchmarks and policy mechanisms. Proposed changes to EU end-of-life-vehicle legislation must be described as proposed or ongoing until enacted. Regulation (EU) 2023/1542 primarily governs batteries and does not establish a traction-motor magnet recycling rate. Regulatory targets must never be entered into material-flow models as observed recovery coefficients [[35]](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:52023PC0451) [[36]](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=legissum%3Al21225) [[37]](https://ec.europa.eu/eurostat/statistics-explained/index.php?title=End-of-life_vehicle_statistics) [[38]](https://environment.ec.europa.eu/topics/waste-and-recycling/end-life-vehicles/end-life-vehicles-regulation_en) [[39]](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex:52023PC0451) [[40]](https://eur-lex.europa.eu/procedure/EN/2023_284) [[41]](https://eur-lex.europa.eu/legal-content/EN/HTML/?uri=OJ:L_202401252) [[42]](https://eur-lex.europa.eu/legal-content/LIT/TXT/?uri=CELEX%3A32024R1252).

The decision implication is straightforward: a credible 2030 model should use route-specific and step-specific parameters, retain an explicit “unknown or other fate” branch, and avoid converting isolated metallurgical yields into a complete recycling rate. By 2060, model scenarios may explore greater collection, automation and short-loop penetration, but these remain assumptions until supported by audited industrial mass balances.

## 2 Methodology and Scope

### 2.1 Review question and functional boundary

The review addresses three questions:

1. What process routes can recover NdFeB magnets and their contained rare earths from end-of-life BEV traction motors?
2. What evidence exists for material transfer coefficients at each stage?
3. Which route or route portfolio is technically plausible as the main system in 2030 and in a 2060 scenario?

The scope boundary is **motor-unit removal**. The foreground system starts with a traction-motor unit that has been identified and removed from the end-of-life vehicle. Capture and motor-removal coefficients are nevertheless retained as upstream multipliers because material that is not captured or does not reach the motor-recycling system cannot be recovered downstream.

The motor boundary includes housing, cooling structures integrated with the housing, stator, rotor, windings, bearings, shaft and permanent magnets. It excludes the traction battery. Gearbox, inverter, differential, cables and retained fluids are excluded where a motor-only boundary can be established. Publicly reported “drive-unit” masses are not treated as motor masses because they may include these excluded components [3] [1] [2].

### 2.2 Architecture boundary

The RAWCLIC composition work distinguishes permanent-magnet motors, induction motors and electrically excited synchronous machines. Its component hierarchy separates the housing, cooling system, stator laminations, windings, rotor laminations, shaft, conductive bars, permanent magnets and gearbox [3] [4].

The magnet-recycling foreground includes:

- radial PMSM and IPM machines containing NdFeB;
- surface-mounted permanent-magnet machines where relevant;
- permanent-magnet axial-flux machines.

It excludes ASM/IM and EESM from the NdFeB chain because those architectures are magnet-free. They remain in the Cu, Al and electrical-steel analysis. The distinction matters because a fleet-level motor collection rate is not automatically an NdFeB collection rate: the collected motor population contains both magnet-bearing and magnet-free machines [3] [1].

### 2.3 Reference motor and material inventory

The reference is a nominal 150 kW PMSM, motor-only. The triplets are planning bounds, not a universal average and not the bill of materials of a named model [1] [2].

| Material or component | Min | Mode/planning centre | Max | Evidence status |
|---|---:|---:|---:|---|
| NdFeB magnets | 1.00 kg | 1.50 kg | 2.00 kg | Bounded engineering range [1] [2] [Reliability: 100%] |
| Nd contained | 0.25 kg | 0.38 kg | 0.55 kg | Composition allowance [1] [2] [Reliability: 100%] |
| Pr contained | 0.03 kg | 0.08 kg | 0.15 kg | Composition allowance [1] [2] [Reliability: 100%] |
| Dy contained | 0.01 kg | 0.05 kg | 0.12 kg | Composition allowance [1] [2] [Reliability: 100%] |
| Tb contained | 0.00 kg | 0.01 kg | 0.03 kg | Composition allowance [1] [2] [Reliability: 100%] |
| Cu | 8 kg | 11 kg | 14 kg | Reference winding inventory [1] [2] [Reliability: 100%] |
| Al | 8 kg | 12 kg | 17 kg | Reference housing inventory [1] [2] [Reliability: 100%] |
| Electrical steel | 28 kg | 37 kg | 46 kg | Stator plus rotor laminations [2] [Reliability: 100%] |

The elemental rows are contained within the NdFeB mass and must not be added to it. The zero minimum for Tb means that Tb may be intentionally absent; it does not imply zero recovery from a magnet that contains Tb.

RAWCLIC’s vehicle-level regression dataset gives a wider range of permanent-magnet masses across segments and torque classes. For example, selected consolidated entries range from approximately 1.5 kg in smaller PM vehicles to more than 4 kg in some larger or higher-torque vehicle classes [4]. Those entries are vehicle-level model outputs and should not be substituted directly for the nominal 150 kW motor-only allowance.

### 2.4 Definition of transfer coefficient

For material \(m\) and process \(i\):

**TC(i,m) = mass of material m in the desired or recoverable output of process i / mass of material m entering process i.**

In words, TC is exactly the **input fraction exiting a process to desired or recoverable output**.

The following controls apply:

- TC is dimensionless and normally lies between zero and one.
- The desired output must be named.
- Purity is not a TC.
- Product concentration is not a TC.
- A legal target is not an observed TC.
- Recycling content is not a TC.
- A laboratory leaching yield is not a full-chain TC.
- A component count is not a material-mass TC unless mass equivalence is demonstrated.
- If an element is not separately measured, Nd, Pr, Dy and Tb must not be assigned different coefficients.
- “NR” means not separately reported or not reportable from the supplied evidence.

The full-chain coefficient for material \(m\) is:

**TC(chain,m) = TC1,m × TC2,m × … × TCn,m.**

This multiplication is valid only where the output boundary of one process matches the input boundary of the next. Coherent low and high chains must represent internally consistent route narratives; unrelated minimum values from different studies must not be multiplied merely because they are minima.

### 2.5 Evidence hierarchy and reliability

The review applies the mandated reliability categories:

- **100%:** peer-reviewed literature, EU legislation and deliverables, standards and JRC publications;
- **80%:** NREL, Argonne, Fraunhofer, USGS, BGS, established market analysts and established specialist press;
- **60%:** supplier, recycler and OEM technical or press material;
- **40%:** recognised general or technical journalism and unreviewed conference papers.

Commercial capacity, performance and recovery claims remain 60% unless independently verified. A high source-reliability rating does not make incomparable process boundaries compatible.

### 2.6 Treatment of scenarios

All 2030 and 2060 Min | Mode | Max bands are to be understood as:

**Scenario parameter ranges synthesized from cited demonstrations/literature; not measured forecasts.**

Where the evidence does not support a numerical band, the table reports **NR | NR | NR**. This is preferable to false completeness. In particular, 2060 is a scenario, not a forecast.

## 3 Motor-Level Recycling: Shredding vs Disassembly Routes

### 3.1 Present industrial context

The current industrial context consists of overlapping routes:

- reuse or resale of a functioning drive unit or motor;
- repair or remanufacturing;
- removal for copper- and aluminium-oriented dismantling;
- transfer to specialist motor recyclers;
- fragmentation within broader metal-recycling systems;
- research, pilot and early commercial magnet-recovery routes.

No compiled source provides an auditable EU-wide percentage distribution among these routes. It would therefore be incorrect to state that all current EV motors are shredded. Equally, the existence of pilot disassembly cells does not establish that selective magnet recovery is already standard fleet-wide practice.

Legacy shredding systems are designed for throughput and recovery of mass-dominant metals. Ferrous metals are separated magnetically, while non-ferrous metals are recovered through additional mechanical and sensor-based operations. This system can recover steel, copper and aluminium effectively enough to sustain established scrap markets, but it was not designed to preserve intact NdFeB magnets or magnet-alloy chemistry [[5]](https://joint-research-centre.ec.europa.eu/jrc-news-and-updates/innovative-requirements-could-boost-circular-economy-plastics-and-critical-raw-materials-vehicles-2023-07-13_en) [[10]](https://doi.org/10.1177/0734242x261476422) [[33]](https://www.okonrecycling.com/magnet-recycling-and-applications/magnet-technology/ev-motor-magnet-recovery/) [[19]](https://www.okonrecycling.com/magnet-recycling-and-applications/magnet-technology/rare-earth-motor-magnet-recycling/) [[8]](https://www.fraunhofer.de/en/press/research-news/2024/january-2024/electromobility-second-life-for-electric-motors.html).

### 3.2 Route A: whole-motor and component disassembly

A deep selective-disassembly route comprises:

1. identification of motor architecture;
2. removal of cables, inverter or gearbox where attached;
3. draining retained fluids where applicable;
4. removal of housing and end shields;
5. bearing and shaft access;
6. separation of rotor and stator;
7. demagnetisation where required;
8. removal of sleeves, bandages, fasteners, adhesives or encapsulants;
9. extraction of magnet segments or liberation of magnet powder;
10. separate routing of aluminium, copper, electrical steel and magnet material.

This depth preserves both concentration and information. A magnet extracted from a known motor retains provenance concerning alloy family, service conditions and geometry; shredded mixed material normally loses that information.

The disadvantages are model diversity, uncertain condition, labour cost and difficult access. Interior permanent magnets may be located in closed rotor pockets and fixed with adhesive or mechanical retention. Surface magnets may be covered by sleeves or bandaging. Strong magnetic forces complicate rotor removal, tool handling and separation from ferrous parts [[14]](https://www.sciencedirect.com/science/article/pii/S0921344924001769) [[43]](https://link.springer.com/article/10.1007/s13243-024-00143-6) [[44]](https://link.springer.com/article/10.1007/s40831-016-0090-4) [[15]](https://link.springer.com/chapter/10.1007/978-3-031-47394-4_45) [[6]](https://link.springer.com/chapter/10.1007/978-3-031-84744-8_6) [[16]](https://www.sciencedirect.com/science/article/pii/S2214993725003549) [[7]](https://www.sciencedirect.com/science/article/pii/S2212827125003786).

### 3.3 Automation and technology readiness

| Operation | Current depth and automation | Indicative status | Main limitation |
|---|---|---|---|
| Motor identification | Nameplate, visual and architecture recognition; emerging sensor and machine-learning classification | Industrial manual practice plus research/pilot automation | Missing identifiers and heterogeneous returns [[45]](https://www.mdpi.com/2673-4591/131/1/11) [[46]](https://pmc.ncbi.nlm.nih.gov/articles/PMC11985978/) [[7]](https://www.sciencedirect.com/science/article/pii/S2212827125003786) [Reliability: 100%] |
| External dehousing | Manual tools and conventional automation for known products | Industrially feasible; automation product-specific | Fastener access, corrosion and integrated housings |
| Rotor–stator separation | Manual lifting or fixtures; robotic path and force-control research | Pilot/demonstration | Magnetic attraction, tight tolerances and unknown damage [[6]](https://link.springer.com/chapter/10.1007/978-3-031-84744-8_6) [[7]](https://www.sciencedirect.com/science/article/pii/S2212827125003786) [Reliability: 100%] |
| Winding removal | Mechanical cutting and pulling; established motor-recycling practice | Commercial for bulk-metal recovery | Copper contamination and damage to laminations |
| Magnet exposure | Cutting, sleeve/bandage removal, adhesive debonding | Mainly manual, pilot or product-specific | Embedded magnets and retention systems [[14]](https://www.sciencedirect.com/science/article/pii/S0921344924001769) [[16]](https://www.sciencedirect.com/science/article/pii/S2214993725003549) [Reliability: 100%] |
| Thermal demagnetisation | Furnace or local heating | Demonstrated and technically mature, but not universal | Energy use, coating degradation and oxidation [[47]](https://www.mdpi.com/2075-4701/14/6/658) [[48]](https://www.sciencedirect.com/science/article/abs/pii/S2452223624000051) [[10]](https://doi.org/10.1177/0734242x261476422) [[12]](https://chemrxiv.org/engage/chemrxiv/article-details/6721e7215a82cea2fa4debeb) [Reliability: 100%] |
| Hydrogen-assisted liberation | Hydrogen exposure and decrepitation | Pilot to early commercial | Sealed equipment, coatings, contamination and feed qualification [[17]](https://www.sciencedirect.com/science/article/pii/S2214993725055123) [[20]](https://www.iwks.fraunhofer.de/en/competencies/MagneticMaterials/Recycling.html) [[9]](https://www.iwks.fraunhofer.de/en/competencies/zdr-emil.html) [[23]](https://hypromagusa.com/technology/) [Reliability: 80%] |
| Flexible robotic disassembly | Vision, force sensing and interchangeable tooling | Research/pilot | Cycle time, product variability and business case [[15]](https://link.springer.com/chapter/10.1007/978-3-031-47394-4_45) [[6]](https://link.springer.com/chapter/10.1007/978-3-031-84744-8_6) [[8]](https://www.fraunhofer.de/en/press/research-news/2024/january-2024/electromobility-second-life-for-electric-motors.html) [[9]](https://www.iwks.fraunhofer.de/en/competencies/zdr-emil.html) [Reliability: 80%] |

A universal TRL cannot be assigned to “motor disassembly” as a single operation. Dehousing a known production motor with dedicated fixtures may be commercially mature, while flexible automated extraction of magnets from mixed unknown rotors remains at pilot or demonstration status. TRL must therefore attach to a defined operation, feed and output.

### 3.4 Demagnetisation

Demagnetisation improves safety and handling and can reduce agglomeration of fragments during mechanical treatment. Reported thermal approaches commonly use elevated temperatures, with some literature describing treatment in the range of approximately 300–500 °C or above the relevant magnetic transition [[47]](https://www.mdpi.com/2075-4701/14/6/658) [[48]](https://www.sciencedirect.com/science/article/abs/pii/S2452223624000051) [[16]](https://www.sciencedirect.com/science/article/pii/S2214993725003549). These are process conditions, not evidence for a universal optimum.

Thermal treatment may:

- reduce attraction between magnet and steel;
- facilitate rotor handling;
- permit mechanical screening after fragmentation;
- degrade adhesives and coatings;
- oxidise exposed powder if atmosphere control is inadequate;
- preclude intact reuse if temperature damages the product.

Hydrogen processing can combine demagnetisation, embrittlement and liberation. It is particularly relevant where direct powder recycling is intended [[17]](https://www.sciencedirect.com/science/article/pii/S2214993725055123) [[20]](https://www.iwks.fraunhofer.de/en/competencies/MagneticMaterials/Recycling.html) [[21]](https://www.iwks.fraunhofer.de/en/projects/current-projects/recyper.html) [[9]](https://www.iwks.fraunhofer.de/en/competencies/zdr-emil.html).

Energy consumption for complete traction-motor demagnetisation is **NR** in the compiled evidence. Temperature alone is insufficient to calculate energy because furnace load, atmosphere, residence time, heat recovery and throughput are not given.

### 3.5 Route B: shredding and mechanical separation

A shredding route may involve:

1. whole-motor or subassembly fragmentation;
2. size classification;
3. magnetic separation;
4. eddy-current and density separation;
5. sensor or manual sorting;
6. production of ferrous, non-ferrous and residue fractions.

Its strengths are throughput, tolerance of heterogeneous products and compatibility with existing scrap infrastructure. Its weakness for NdFeB is loss of concentration. Brittle magnet fragments can adhere to steel, become distributed between fractions or oxidise. Subsequent steelmaking is not automatically a rare-earth recovery process.

The consequences depend strongly on pretreatment:

- **Untreated shredding:** magnetised fragments may agglomerate with ferrous scrap.
- **Demagnetisation before shredding:** fragments can be screened more selectively.
- **Rotor-only controlled comminution:** feed dilution is lower than for a complete motor.
- **Whole-vehicle shredding:** the magnet inventory is diluted into a much larger and more heterogeneous stream.

The reported increase from approximately 9.47% to 50.8% NdFeB concentration demonstrates enrichment after thermal and mechanical treatment [[10]](https://doi.org/10.1177/0734242x261476422) [[11]](https://pubmed.ncbi.nlm.nih.gov/42625283/) [[12]](https://chemrxiv.org/engage/chemrxiv/article-details/6721e7215a82cea2fa4debeb) [[13]](https://link.springer.com/article/10.1007/s12649-026-03754-1). It does not disclose enough information to calculate total-magnet recovery unless the masses of every output stream and their NdFeB concentrations are known.

### 3.6 Route comparison

| Criterion | Selective disassembly | Controlled shredding after demagnetisation | Conventional mixed shredding |
|---|---|---|---|
| Magnet concentration | Highest potential | Intermediate to high if rotor feed is controlled | Usually diluted |
| Intact reuse possible | Yes | No | No |
| Short-loop compatibility | High for clean, identified magnets | Possible after effective concentration and cleaning | Low without additional upgrading |
| Mixed-feed tolerance | Low to medium | Medium to high | High |
| Throughput | Lower | Higher | Highest |
| Automation status | Product-specific commercial; flexible systems pilot | Mechanical equipment mature; integrated magnet recovery demonstrated | Commercial bulk-metal route |
| Information retention | High | Medium to low | Low |
| Cu/Al/steel recovery | High if components are sorted | High potential | Established but quality depends on separation |
| Public full-chain TC | NR | NR | NR |
| Energy consumption | NR | NR | NR |

The preferable route is not determined by magnet value alone. A functioning motor may justify reuse; a known rotor with clean magnets may justify selective extraction; a damaged and contaminated unit may require controlled fragmentation and long-loop metallurgy.

## 4 NdFeB Magnet Recycling Processes — Inventory and Status

### 4.1 Direct reuse

Direct reuse retains the magnet as a magnet. The operations may include demagnetisation for handling, extraction, coating removal or repair, dimensional inspection, magnetic characterisation, re-coating, remagnetisation and qualification.

Its theoretical advantage is maximum preservation of embodied processing and geometry. Its practical limitations are demanding:

- magnet dimensions must match a new application;
- corrosion or edge damage may be unacceptable;
- thermal history and partial demagnetisation must be understood;
- coatings and adhesives may be difficult to remove;
- traceability is needed for automotive qualification.

The compiled sources discuss functional recycling and value-retention hierarchies but do not provide a representative traction-motor direct-reuse yield [[49]](https://link.springer.com/chapter/10.1007/978-3-032-21154-5_22) [[50]](https://www.researchgate.net/publication/389513583_Functional_Recycling_and_Reuse_of_Nd-Fe-B_Permanent_Magnets_from_Various_Waste_Streams_for_a_more_Sustainable_and_Resilient_Electromobility) [[8]](https://www.fraunhofer.de/en/press/research-news/2024/january-2024/electromobility-second-life-for-electric-motors.html). Accordingly:

- material recovery: **NR**;
- energy consumption: **NR**;
- status: demonstration or niche product-specific practice, not established fleet-wide reuse;
- likely role: small, high-value branch before material recycling.

### 4.2 Hydrogen decrepitation and HPMS

Hydrogen decrepitation exploits the reaction of hydrogen with NdFeB phases. Expansion and embrittlement break the magnet into particles. In HPMS, hydrogen can penetrate exposed magnets within an assembly and assist liberation of powder from surrounding steel.

A short-loop process may include:

1. feed inspection and removal of incompatible material;
2. hydrogen treatment;
3. physical separation of powder from steel and coatings;
4. sieving and cleaning;
5. composition analysis;
6. blending with virgin alloy or other recycled powder;
7. milling, alignment and pressing;
8. sintering and heat treatment;
9. machining, coating and magnetisation.

The route avoids complete chemical separation into individual rare-earth products. That advantage also creates a constraint: undesirable chemistry is retained unless removed physically or corrected by blending. Oxygen, carbon, nickel or copper coatings, adhesives and mixed magnet grades can impair new-magnet performance [[18]](https://www.fastmarkets.com/insights/rare-earth-magnet-recycling-technology-branches-out/) [[19]](https://www.okonrecycling.com/magnet-recycling-and-applications/magnet-technology/rare-earth-motor-magnet-recycling/) [[20]](https://www.iwks.fraunhofer.de/en/competencies/MagneticMaterials/Recycling.html) [[21]](https://www.iwks.fraunhofer.de/en/projects/current-projects/recyper.html) [[9]](https://www.iwks.fraunhofer.de/en/competencies/zdr-emil.html).

Status is pilot to early commercial. HyProMag and associated programmes report commercial-scale development in the United Kingdom and Germany, while Fraunhofer projects demonstrate hydrogen-assisted recovery and production of recycled magnet material [[20]](https://www.iwks.fraunhofer.de/en/competencies/MagneticMaterials/Recycling.html) [[21]](https://www.iwks.fraunhofer.de/en/projects/current-projects/recyper.html) [[9]](https://www.iwks.fraunhofer.de/en/competencies/zdr-emil.html) [[22]](https://rare-earth-mining.com/hypromag/) [[23]](https://hypromagusa.com/technology/) [[24]](https://hypromag.com/executive-summary-of-recent-technical-progress-by-hypromag-ltd-june-2025/) [[25]](https://hypromag.com/about/). Supplier statements are rated 60%; Fraunhofer evidence is rated 80%.

No independently audited traction-motor-to-qualified-new-magnet mass recovery is available in the compiled evidence. Claims of substantially lower energy demand than primary production refer to broader comparative assessments or supplier statements and do not provide a consistent kWh/kg boundary here [[22]](https://rare-earth-mining.com/hypromag/) [[23]](https://hypromagusa.com/technology/). Energy is therefore **NR**.

### 4.3 HDDR

HDDR comprises hydrogenation, disproportionation, desorption and recombination. Unlike simple decrepitation, it deliberately transforms and reconstructs the NdFeB microstructure. It can refine grains and produce powder suitable for subsequent magnet manufacture.

Potential applications include:

- upgrading coarser recycled alloy;
- producing anisotropic powder;
- bonded magnets;
- feed preparation before consolidation.

The route requires controlled temperature, pressure and time. Oxidation and composition drift remain important. HDDR should be regarded as a specialised powder-processing route rather than the default treatment for complete motors. The compiled evidence supports laboratory and pilot relevance but does not demonstrate a dominant commercial EoL traction-motor route [[26]](https://pubs.acs.org/acsodf/article/8/20/17431/407376/Review-on-the-Parameters-of-Recycling-NdFeB) [[27]](https://pmc.ncbi.nlm.nih.gov/articles/PMC12897740/) [[28]](https://research.birmingham.ac.uk/en/publications/recycling-of-ndfeb-magnets-from-hard-disc-drive-scrap-using-hpms-/) [[29]](https://link.springer.com/article/10.1007/s10163-025-02162-2) [[30]](https://onlinelibrary.wiley.com/doi/10.1155/2014/638013) [[51]](https://iopscience.iop.org/article/10.1088/1361-6668/ad54f5).

Recovery rate: **NR**.  
Energy consumption: **NR**.  
Status: research to pilot, with industrial magnet-powder know-how but limited public motor-specific mass balance.

### 4.4 Conventional direct remanufacturing

Conventional direct recycling can also involve crushing, cleaning, re-milling and re-sintering without elemental separation. It is a short-loop route if the alloy remains substantially intact.

Advantages are fewer chemical transformations and potentially lower waste generation. Limitations are similar to HPMS: mixed grades, oxidation and contaminants. The process is most credible for segregated manufacturing scrap and known magnets; EoL motor feed is more challenging because extraction and service history introduce uncertainty [[47]](https://www.mdpi.com/2075-4701/14/6/658) [[14]](https://www.sciencedirect.com/science/article/pii/S0921344924001769) [[52]](https://www.mdpi.com/2075-4701/15/11/1227) [[27]](https://pmc.ncbi.nlm.nih.gov/articles/PMC12897740/) [[53]](https://www.mdpi.com/2071-1050/13/17/9668) [[54]](https://www.mdpi.com/1996-1073/11/4/792).

Recovery and energy: **NR** for complete traction-motor feed.

### 4.5 Hydrometallurgy

A generic hydrometallurgical route comprises:

1. magnet liberation and size reduction;
2. optional oxidation or roasting;
3. acid or alternative-solvent leaching;
4. solid–liquid separation;
5. removal of iron, boron and coating-derived impurities;
6. separation of rare-earth elements or production of a mixed rare-earth product;
7. precipitation;
8. calcination to oxide;
9. optional conversion to fluoride, metal or alloy.

Hydrometallurgy can treat oxidised, mixed or low-grade material and can produce separated rare-earth products. The penalty is a longer loop, reagent use and effluent management. Iron is the dominant mass in NdFeB, so selectivity is important.

Reported values above 99% generally refer to leaching or a specified recovery stage under controlled conditions [[31]](https://www.mdpi.com/2227-9717/13/6/1729) [[32]](https://pubs.rsc.org/en/content/articlehtml/2025/cc/d4cc04252b) [[33]](https://www.okonrecycling.com/magnet-recycling-and-applications/magnet-technology/ev-motor-magnet-recovery/) [[19]](https://www.okonrecycling.com/magnet-recycling-and-applications/magnet-technology/rare-earth-motor-magnet-recycling/). A 99.8% value is attributed to a recycler claim and is not an independently audited full-chain result [[34]](https://www.reecycleinc.com/recycle-electric-motor-magnets). These figures must not be multiplied into a model as though they included capture, motor removal and magnet extraction.

Status ranges from laboratory to commercial depending on the operation. Acid leaching, solvent extraction, precipitation and oxide production are industrially established unit operations. Their integrated application to EoL traction-motor magnets is emerging, with commercial claims and scale-up activity but limited public plant-wide mass balances [[33]](https://www.okonrecycling.com/magnet-recycling-and-applications/magnet-technology/ev-motor-magnet-recovery/) [[34]](https://www.reecycleinc.com/recycle-electric-motor-magnets) [[18]](https://www.fastmarkets.com/insights/rare-earth-magnet-recycling-technology-branches-out/) [[19]](https://www.okonrecycling.com/magnet-recycling-and-applications/magnet-technology/rare-earth-motor-magnet-recycling/) [[55]](https://www.ifam.fraunhofer.de/en/Aboutus/Locations/Dresden/HydrogenTechnology/recycling.html) [[56]](https://www.igb.fraunhofer.de/en/reference-projects/fraunhofer-lighthouse-project-critical-rare-earths.html) [[57]](https://www.materials.fraunhofer.de/en/business-areas/energy_and_environment/recycling-of-rare-eart-magnets.html).

Energy consumption: **NR** on a compatible motor-to-product basis.

### 4.6 Pyrometallurgy

Pyrometallurgical options include oxidation, chlorination, molten-salt processing, selective slagging, liquid-metal extraction and smelting. Their common attraction is tolerance of heterogeneous feed and the ability to separate bulk Fe, Cu and Al while concentrating rare earths.

A reported single-furnace route uses melting-point differences and a fayalite flux to transfer rare earths to a slag, with neodymium extraction of up to 91% [[31]](https://www.mdpi.com/2227-9717/13/6/1729). The result is route- and condition-specific. The slag still requires downstream treatment to produce a usable rare-earth compound or metal.

Other studied routes use magnesium or other liquid metals to extract rare earths from magnet scrap, followed by distillation or alloy recovery [[17]](https://www.sciencedirect.com/science/article/pii/S2214993725055123) [[32]](https://pubs.rsc.org/en/content/articlehtml/2025/cc/d4cc04252b) [[58]](https://link.springer.com/chapter/10.1007/978-3-031-81182-1_5). Molten-salt electrochemical approaches are also under development [[32]](https://pubs.rsc.org/en/content/articlehtml/2025/cc/d4cc04252b) [[59]](https://link.springer.com/article/10.1007/s40831-018-0198-9).

Status ranges from laboratory to pilot. High-temperature metal recovery itself is commercially mature, but selective rare-earth recovery from traction-motor NdFeB is not demonstrated as a universal commercial chain.

Energy consumption: **NR**. The qualitative statement that high-temperature processing is energy intensive does not substitute for a measured motor-specific value.

### 4.7 Short-loop versus long-loop

| Route | Product | Composition tolerance | Value retention | Status for EoL motor magnets | Supported recovery |
|---|---|---|---|---|---|
| Direct reuse | Intact magnet | Very low | Highest | Niche/demonstration | NR |
| HD/HPMS | Recycled alloy powder/new magnet | Low to medium | High | Pilot to early commercial [[20]](https://www.iwks.fraunhofer.de/en/competencies/MagneticMaterials/Recycling.html) [[21]](https://www.iwks.fraunhofer.de/en/projects/current-projects/recyper.html) [[22]](https://rare-earth-mining.com/hypromag/) [[23]](https://hypromagusa.com/technology/) | NR for full route |
| HDDR | Upgraded powder | Low to medium | High | Research/pilot | NR |
| Direct re-sintering | New magnet | Low | High | Demonstrated; stronger for clean scrap | NR |
| Hydrometallurgy | Mixed or separated RE compounds | High | Lower material-function retention | Unit operations commercial; motor-feed integration emerging | >99% for selected stages [[31]](https://www.mdpi.com/2227-9717/13/6/1729) [[32]](https://pubs.rsc.org/en/content/articlehtml/2025/cc/d4cc04252b) [Reliability: 100%]; 99.8% supplier claim [[34]](https://www.reecycleinc.com/recycle-electric-motor-magnets) [Reliability: 60%] |
| Pyrometallurgy plus hydrometallurgy | RE-rich slag/alloy, then compounds | High | Lower | Laboratory/pilot for selective motor-magnet recovery | Up to 91% Nd extraction in one reported furnace route [[31]](https://www.mdpi.com/2227-9717/13/6/1729) [Reliability: 100%] |

Short-loop and long-loop are complementary. Short-loop processing is preferable where composition and contamination are controlled. Long-loop processing is the fallback where purification and elemental flexibility are more valuable than retaining the original alloy.

## 5 Transfer Coefficients: Full Chain Analysis

### 5.1 Step definitions and evidence controls

The chain is defined as:

1. EoL capture;
2. motor removal;
3. dehousing and demagnetisation;
4a. selective magnet extraction;
4b. alternative shredding fate;
5. principal magnet-recycling process;
6. REE separation and purification;
7. REE oxide or metal production.

Step 4a and Step 4b are mutually exclusive route branches. They must not be multiplied together.

The evidence is insufficient to provide measured forecasting distributions for 2030 or 2060. The tables below are therefore **scenario parameter ranges synthesized from cited demonstrations/literature; not measured forecasts**. NR is retained wherever derivation would require an unsupported assumption.

### 5.2 2030 scenario-parameter table

**2030 Min | Mode | Max values are scenario parameter ranges synthesized from cited demonstrations/literature; not measured forecasts.**

| Step and desired output | Total NdFeB | Nd | Pr | Dy | Tb | Cu | Al | Electrical steel |
|---|---|---|---|---|---|---|---|---|
| 1 EoL capture: motor-bearing EoL vehicle reaches authorised treatment | NR \| NR \| NR | NR | NR | NR | NR | NR | NR | NR |
| 2 Motor removal: traction motor reaches motor-specific treatment | NR \| NR \| NR | Same total-magnet proxy; element-specific fate NR | Same | Same | Same | NR | NR | NR |
| 3 Dehousing/demagnetisation: target component reaches extraction feed | NR \| NR \| NR | Same total-magnet proxy; no elemental separation | Same | Same | Same | NR | NR | NR |
| 4a Magnet extraction: liberated magnet or magnet-rich powder | NR \| NR \| NR | Same total-magnet proxy | Same | Same | Same | Not meaningful for magnet branch | Not meaningful | Not meaningful |
| 4b Shredding: NdFeB reports to recoverable enriched fraction | NR \| NR \| NR; concentration increased from 9.47% to 50.8%, but TC cannot be derived without stream masses [[10]](https://doi.org/10.1177/0734242x261476422) [[11]](https://pubmed.ncbi.nlm.nih.gov/42625283/) [[12]](https://chemrxiv.org/engage/chemrxiv/article-details/6721e7215a82cea2fa4debeb) [[13]](https://link.springer.com/article/10.1007/s12649-026-03754-1) [Reliability: 100%] | Not separately reported (NR) | NR | NR | NR | NR | NR | NR |
| 5 Short-loop HD/HPMS: acceptable recycled alloy/new-magnet feed | NR \| NR \| NR [[17]](https://www.sciencedirect.com/science/article/pii/S2214993725055123) [[20]](https://www.iwks.fraunhofer.de/en/competencies/MagneticMaterials/Recycling.html) [[21]](https://www.iwks.fraunhofer.de/en/projects/current-projects/recyper.html) [[23]](https://hypromagusa.com/technology/) [Reliability: 80%] | Not separately reported; alloy retained | Same | Same | Same | Not applicable | Not applicable | Not applicable |
| 5 Hydrometallurgical alternative: REE-bearing solution/product | NR \| NR \| NR; selected stages >99%, not a full-route TC [[31]](https://www.mdpi.com/2227-9717/13/6/1729) [[32]](https://pubs.rsc.org/en/content/articlehtml/2025/cc/d4cc04252b) [Reliability: 100%] | Usually total-REE or Nd-specific; route-specific NR | NR | NR | NR | Not applicable | Not applicable | Not applicable |
| 5 Pyrometallurgical alternative: REE-rich slag/alloy | NR \| NR \| NR | Up to 0.91 Nd extraction in one demonstration [[31]](https://www.mdpi.com/2227-9717/13/6/1729) [Reliability: 100%] | NR | NR | NR | NR | NR | NR |
| 6 REE separation and purification: separated RE compound | Not meaningful as total NdFeB | NR \| NR \| NR | NR \| NR \| NR | NR \| NR \| NR | NR \| NR \| NR | Not applicable | Not applicable | Not applicable |
| 7 RE oxide/metal production: specification-grade product | Not meaningful as total NdFeB | NR \| NR \| NR | NR \| NR \| NR | NR \| NR \| NR | NR \| NR \| NR | Not applicable | Not applicable | Not applicable |

The absence of numbers is not an assumption of zero. It means that no compatible numerical coefficient is supported by the compiled evidence.

For scenario construction outside the evidence layer, a modeller may assign policy or engineering parameters to the NR cells, but every assigned value must be tagged “scenario assumption” and kept separate from measured or demonstrated data. The mode cannot be presented as an observed central estimate.

### 5.3 2060 scenario and coherent chain calculations

**2060 is a scenario, not a forecast.** Its Min | Mode | Max values are scenario parameter ranges synthesized from cited demonstrations/literature; not measured forecasts.

| Step and desired output | Total NdFeB | Nd | Pr | Dy | Tb | Cu | Al | Electrical steel |
|---|---|---|---|---|---|---|---|---|
| 1 EoL capture | NR \| NR \| NR | NR | NR | NR | NR | NR | NR | NR |
| 2 Motor removal | NR \| NR \| NR | Total-magnet proxy only | Same | Same | Same | NR | NR | NR |
| 3 Dehousing/demagnetisation | NR \| NR \| NR | Total-magnet proxy only | Same | Same | Same | NR | NR | NR |
| 4a Selective extraction | NR \| NR \| NR | Total-magnet proxy only | Same | Same | Same | Not meaningful | Not meaningful | Not meaningful |
| 4b Controlled shredding alternative | NR \| NR \| NR | NR | NR | NR | NR | NR | NR | NR |
| 5 Short-loop process | NR \| NR \| NR | Alloy proxy; elemental coefficients not separately reported | Same | Same | Same | Not applicable | Not applicable | Not applicable |
| 5 Long-loop process | NR \| NR \| NR | Route-specific NR | NR | NR | NR | Not applicable | Not applicable | Not applicable |
| 6 REE separation/purification | Not meaningful | NR \| NR \| NR | NR \| NR \| NR | NR \| NR \| NR | NR \| NR \| NR | Not applicable | Not applicable | Not applicable |
| 7 Oxide/metal production | Not meaningful | NR \| NR \| NR | NR \| NR \| NR | NR \| NR \| NR | NR \| NR \| NR | Not applicable | Not applicable | Not applicable |

A numerical overall NdFeB-to-recovered-REE TC cannot be calculated without inventing upstream and downstream values. The transparent formula is nevertheless:

**TC(chain, Nd) = TCcapture,Nd × TCremoval,Nd × TCdehousing,Nd × TCextraction,Nd × TCprocess,Nd × TCseparation,Nd × TCoxide/metal,Nd.**

Equivalent expressions apply to Pr, Dy and Tb.

For steps 1–5, where the literature does not report element-specific partitioning, a common total-magnet or total-REE proxy would have to be used:

**TC1,Nd = TC1,Pr = TC1,Dy = TC1,Tb = TC1,total-magnet proxy**, and similarly for steps 2–5.

This equality is a modelling assumption, not a measured fact. It may be reasonable before chemical separation because the elements reside in the same magnet particles, but selective oxidation, slag partitioning, leaching, precipitation and separation can cause element-specific behaviour at steps 5–7. Element-specific precision must therefore not be claimed for those stages without measurements.

#### Demonstration-only partial calculations

The following examples show what can and cannot be calculated.

- If a pyrometallurgical experiment reports 91% Nd extraction, then **TC(process-stage,Nd) = 0.91** for that experiment and its defined feed and output [[31]](https://www.mdpi.com/2227-9717/13/6/1729). The full-chain TC remains NR because capture, removal, liberation, purification and metal production are missing.
- If a hydrometallurgical experiment reports more than 99% recovery at a selected stage, the stage TC is greater than 0.99 under the experimental conditions [[31]](https://www.mdpi.com/2227-9717/13/6/1729) [[32]](https://pubs.rsc.org/en/content/articlehtml/2025/cc/d4cc04252b). It must not be applied automatically to Pr, Dy or Tb, nor to the complete motor chain.
- A concentration increase from 9.47% to 50.8% does not yield a TC. If feed mass is \(M_f\), product mass is \(M_p\), feed concentration is 0.0947 and product concentration is 0.508, the magnet TC would be:  
  **TC = (0.508 × M_p) / (0.0947 × M_f).**  
  Because \(M_p/M_f\) is not reported in the compiled evidence, the result is NR [[10]](https://doi.org/10.1177/0734242x261476422) [[11]](https://pubmed.ncbi.nlm.nih.gov/42625283/) [[12]](https://chemrxiv.org/engage/chemrxiv/article-details/6721e7215a82cea2fa4debeb).

#### Distinct shredding-route comparison

| Shredding route | Desired output | Evidence-supported TC |
|---|---|---|
| Whole motor, no magnet-specific pretreatment | NdFeB-rich recoverable fraction | NR; literature reports dispersion and attachment to ferrous material but no universal coefficient [[10]](https://doi.org/10.1177/0734242x261476422) [[33]](https://www.okonrecycling.com/magnet-recycling-and-applications/magnet-technology/ev-motor-magnet-recovery/) [[19]](https://www.okonrecycling.com/magnet-recycling-and-applications/magnet-technology/rare-earth-motor-magnet-recycling/) [Reliability: 100%/60% according to source type] |
| Thermal demagnetisation plus shredding and screening | Magnet-enriched fraction | NR; 50.8% product concentration reported, but mass yield absent [[10]](https://doi.org/10.1177/0734242x261476422) [[11]](https://pubmed.ncbi.nlm.nih.gov/42625283/) [[12]](https://chemrxiv.org/engage/chemrxiv/article-details/6721e7215a82cea2fa4debeb) [Reliability: 100%] |
| Rotor-only controlled fragmentation | Magnet-rich fraction | NR |
| Whole-vehicle shredding | Recoverable NdFeB product | NR; no evidence supports a universal near-zero numerical TC |

No route is assigned zero merely because recovery is difficult. Conversely, recovery of the ferrous fraction must not be counted as recovery of the contained rare earths unless a downstream operation deliberately recovers them.

## 6 Main Process in 2030 and 2060: Comparison and Transition Drivers

### 6.1 Most plausible 2030 configuration

The most plausible 2030 system is a **hybrid selective-recovery portfolio**:

1. removal of the motor unit before indiscriminate vehicle fragmentation where operationally and legally required;
2. triage between reuse, remanufacturing and material recycling;
3. dehousing and rotor–stator separation;
4. manual or semi-automated access to the magnet-bearing rotor;
5. hydrogen-assisted or mechanical extraction for compatible NdFeB;
6. short-loop magnet-to-magnet recycling for clean, known material;
7. hydrometallurgical recovery for mixed, oxidised or contaminated material;
8. controlled shredding and enrichment where extraction is uneconomic.

This route is better supported than either of two extremes: continued reliance on mixed shredding for all motors, or universal non-destructive magnet extraction. Current projects demonstrate the technical components of selective treatment, but feed volumes, motor diversity and qualification requirements will constrain full deployment [[6]](https://link.springer.com/chapter/10.1007/978-3-031-84744-8_6) [[8]](https://www.fraunhofer.de/en/press/research-news/2024/january-2024/electromobility-second-life-for-electric-motors.html) [[20]](https://www.iwks.fraunhofer.de/en/competencies/MagneticMaterials/Recycling.html) [[21]](https://www.iwks.fraunhofer.de/en/projects/current-projects/recyper.html) [[9]](https://www.iwks.fraunhofer.de/en/competencies/zdr-emil.html) [[60]](https://cordis.europa.eu/article/id/413346-designing-and-recycling-electric-motors) [[61]](https://cordis.europa.eu/docs/results/310/310240/final1-remanence-final-report-v1.pdf).

Hydrogen processing is the leading candidate for the main short-loop magnet process because it combines liberation and alloy recovery and has moved toward early commercial deployment [[17]](https://www.sciencedirect.com/science/article/pii/S2214993725055123) [[18]](https://www.fastmarkets.com/insights/rare-earth-magnet-recycling-technology-branches-out/) [[20]](https://www.iwks.fraunhofer.de/en/competencies/MagneticMaterials/Recycling.html) [[22]](https://rare-earth-mining.com/hypromag/) [[23]](https://hypromagusa.com/technology/). Hydrometallurgy remains indispensable because not every recovered magnet stream will satisfy short-loop chemistry requirements.

### 6.2 2060 circular-routing scenario

The 2060 case is explicitly a **scenario, not a forecast**. Its defining feature is not a single dominant reactor. It is information-rich routing:

- functioning motors to reuse or remanufacturing;
- serviceable magnets to direct reuse;
- known compatible alloys to HPMS, HD, HDDR or direct re-sintering;
- mixed and oxidised magnets to hydrometallurgy;
- highly heterogeneous assemblies to controlled thermal, mechanical and pyrometallurgical concentration;
- residues to secondary recovery only where technically and environmentally justified.

Such a system would require durable identification, digital composition records, standardised magnet labels, accessible fastening and debonding, reverse-logistics contracts and qualification standards for recycled magnets. These institutional and design conditions may dominate the achievable chain TC.

### 6.3 Transition drivers

**Regulation.** Removal and information requirements can prevent magnet-bearing motors from disappearing into mixed material flows. CRMA benchmarks and strategic projects can support European capacity, but targets are not achieved recovery rates [[35]](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:52023PC0451) [[36]](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=legissum%3Al21225) [[37]](https://ec.europa.eu/eurostat/statistics-explained/index.php?title=End-of-life_vehicle_statistics) [[62]](https://rmis.jrc.ec.europa.eu/uploads/CRMs_for_Strategic_Technologies_and_Sectors_in_the_EU_2020.pdf) [[39]](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex:52023PC0451).

**Feedstock volume.** Commercial plants require predictable quantities and chemistry. Production scrap is cleaner and currently easier to recycle than mixed end-of-life motor magnets. Larger EoL flows can improve utilisation but also increase heterogeneity.

**Magnet prices and supply security.** Higher NdPr or heavy-rare-earth prices favour deeper disassembly. Low primary-material prices can weaken the business case even where recycling is technically successful.

**Design for disassembly.** Accessible rotors, reversible joining, reduced adhesive contamination and standardised identifiers can lower extraction cost. EU projects have demonstrated motors designed so that magnets can be removed more readily [[60]](https://cordis.europa.eu/article/id/413346-designing-and-recycling-electric-motors) [[61]](https://cordis.europa.eu/docs/results/310/310240/final1-remanence-final-report-v1.pdf).

**Automation.** Robotic systems can improve safety and repeatability, but they require product recognition and adaptable end-effectors. Automation is most economic where motor families and volumes are stable [[15]](https://link.springer.com/chapter/10.1007/978-3-031-47394-4_45) [[6]](https://link.springer.com/chapter/10.1007/978-3-031-84744-8_6) [[7]](https://www.sciencedirect.com/science/article/pii/S2212827125003786) [[8]](https://www.fraunhofer.de/en/press/research-news/2024/january-2024/electromobility-second-life-for-electric-motors.html) [[9]](https://www.iwks.fraunhofer.de/en/competencies/zdr-emil.html).

**Qualification.** Automotive magnets must meet magnetic, thermal, mechanical, coating and durability requirements. A high chemical recovery rate does not guarantee acceptance in a traction motor.

**Architecture change.** Expansion of EESM and induction designs reduces the NdFeB feedstock per vehicle, while permanent-magnet axial-flux adoption sustains magnet demand. Scenario work suggests diversification away from current PM dominance, but long-term architecture shares are uncertain [1] [2].

### 6.4 Comparative decision matrix

| Criterion | Direct reuse | HD/HPMS short loop | HDDR/direct powder route | Hydrometallurgy | Pyro + hydro | Controlled shredding |
|---|---:|---:|---:|---:|---:|---:|
| Value retention | Highest | High | High | Medium | Low–medium | Depends on downstream route |
| Feed tolerance | Low | Low–medium | Low–medium | High | High | High |
| Element separation | No | No | No | Yes | Usually downstream | No |
| Public motor-specific mass balance | NR | NR | NR | Sparse | Sparse | Sparse |
| Industrial status by 2030 | Niche | Pilot/early commercial to scaling | Pilot/specialised | Commercial unit operations; motor integration scaling | Pilot/specialised | Commercial mechanics; magnet recovery conditional |
| Likely 2060 role | Selective | Major clean-feed route | Specialised upgrading | Major mixed-feed route | Residual/mixed-feed route | Pretreatment, not final recovery |
| Energy evidence | NR | NR | NR | NR | NR | NR |

## 7 Copper, Aluminium and Electrical Steel — TC Summary

Copper, aluminium and electrical steel dominate motor mass and already have established scrap markets. Their recovery cannot nevertheless be represented by magnet-process coefficients.

Copper is concentrated in stator windings and, in EESMs, may also be present in rotor windings. The nominal 150 kW PMSM contains 8 | 11 | 14 kg copper; an EESM scenario adds an estimated 3 | 6 | 10 kg rotor copper [1] [2]. Aluminium is concentrated in housing and cooling structures, while electrical steel is found in the stator and rotor laminations.

Selective disassembly can produce cleaner outputs:

- aluminium housing separated before ferrous processing;
- winding copper removed mechanically;
- laminations separated from copper and magnets;
- shafts and bearings routed separately.

Shredding can achieve high bulk-metal recovery, but output quality depends on liberation and separation. Copper attached to laminations can contaminate steel. Aluminium casting alloys may be mixed with other non-ferrous grades. Thin electrical-steel laminations may lose their functional value and normally become metallurgical scrap rather than new motor laminations.

### Scenario TC summary

**The table contains scenario-parameter placeholders, not measured forecasts. No compatible motor-specific Min | Mode | Max dataset was supplied.**

| Material and stage | 2030 Min \| Mode \| Max | 2060 Min \| Mode \| Max | Interpretation |
|---|---|---|---|
| Cu: motor capture and removal | NR \| NR \| NR | NR \| NR \| NR | Same upstream uncertainty as motor collection |
| Cu: winding liberation to copper-rich output | NR \| NR \| NR | NR \| NR \| NR | Industrially practiced, but motor-specific TC not reported |
| Cu: specification secondary copper | NR \| NR \| NR | NR \| NR \| NR | Smelter/refinery boundary absent |
| Al: housing separation | NR \| NR \| NR | NR \| NR \| NR | Product-specific dehousing evidence lacks mass balance |
| Al: secondary alloy production | NR \| NR \| NR | NR \| NR \| NR | Alloy dilution and refining not quantified |
| Electrical steel: ferrous recovery | NR \| NR \| NR | NR \| NR \| NR | Ferrous collection is not equivalent to functional lamination reuse |
| Electrical steel: new lamination-grade material | NR \| NR \| NR | NR \| NR \| NR | Functional recycling not separately reported |

For modelling, two outputs should be distinguished:

1. **material recovery**, such as copper entering a secondary-copper process; and
2. **functional closed-loop recovery**, such as electrical steel becoming new motor-grade sheet.

The second coefficient will generally be no greater than the first, but the evidence does not quantify the difference. It must not be inferred from gross metal recycling targets.

## 8 Regulatory Framework (CRMA, ELVD, EU Battery Regulation)

### 8.1 Critical Raw Materials Act

Regulation (EU) 2024/1252—the Critical Raw Materials Act—is enacted EU law. It establishes a framework for secure and sustainable supplies of critical raw materials, including strategic benchmarks, monitoring, strategic projects, circularity measures and supply-risk reduction [[35]](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:52023PC0451) [[36]](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=legissum%3Al21225) [[63]](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=COM%3A2023%3A451%3AFIN&qid=1689318552193) [[64]](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=LEGISSUM:l21225) [[37]](https://ec.europa.eu/eurostat/statistics-explained/index.php?title=End-of-life_vehicle_statistics) [[62]](https://rmis.jrc.ec.europa.eu/uploads/CRMs_for_Strategic_Technologies_and_Sectors_in_the_EU_2020.pdf) [[39]](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex:52023PC0451).

Its relevance to motor recycling is strategic rather than a direct motor-level recovery coefficient. It can support:

- European rare-earth separation and magnet capacity;
- recycling projects;
- improved information on permanent magnets;
- reduced dependence on concentrated external supply;
- assessment of circularity and secondary-material availability.

Any CRMA recycling benchmark is a policy target at the relevant aggregate boundary. It is not evidence that 25% of rare earths in an individual motor, or in the EU motor stock, is currently recovered. It must not be used as TCcapture, TCextraction or TCprocess.

### 8.2 End-of-Life Vehicles Directive and proposed changes

The existing ELV framework and the Commission’s proposed transition toward a regulation address vehicle design, treatment, reuse, recycling and producer responsibility. The compiled EU evidence discusses improved removal of electric-drive motors and information or labelling for permanent magnets [[65]](https://publications.jrc.ec.europa.eu/repository/bitstream/JRC140892/JRC140892_01.pdf) [[5]](https://joint-research-centre.ec.europa.eu/jrc-news-and-updates/innovative-requirements-could-boost-circular-economy-plastics-and-critical-raw-materials-vehicles-2023-07-13_en) [[66]](https://op.europa.eu/en/publication-detail/-/publication/34274068-ee70-11ef-b5e9-01aa75ed71a1/language-en) [[38]](https://environment.ec.europa.eu/topics/waste-and-recycling/end-life-vehicles/end-life-vehicles-regulation_en) [[67]](https://environment.ec.europa.eu/topics/waste-and-recycling/end-life-vehicles_en) [[68]](https://ec.europa.eu/environment/pdf/waste/elv/ELV_report.pdf) [[69]](https://ec.europa.eu/eurostat/statistics-explained/index.php?title=End-of-life_vehicle_statistics&oldid=545041) [[70]](https://ec.europa.eu/environment/pdf/waste/studies/elv/compliance_art7_2.pdf).

The legal status must be stated precisely:

- the current ELV legal framework is enacted;
- proposed replacement or amendment provisions remain proposed or under legislative negotiation until formally adopted;
- proposed pre-shredding removal or design provisions are not present-day achieved recovery rates.

For modelling, regulation may justify a scenario in which motor removal becomes more systematic. It does not provide the numerical motor-removal TC unless compliance data demonstrate actual implementation.

### 8.3 EU Battery Regulation

Regulation (EU) 2023/1542 principally governs batteries and waste batteries. Its provisions include battery sustainability, information, collection, recycling and recycled-content requirements at battery-related boundaries [[71]](https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:52025DC0260) [[72]](https://eur-lex.europa.eu/EN/legal-content/summary/deployment-of-alternative-fuels-infrastructure.html) [[73]](https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX%3A42023X0401) [[74]](https://eur-lex.europa.eu/eli/dir/2006/126/2020-11-01/eng) [[75]](https://eur-lex.europa.eu/EN/legal-content/summary/road-safety-driving-licences.html) [[76]](https://eur-lex.europa.eu/EN/legal-content/summary/two-or-three-wheeled-motor-vehicles-maximum-design-speed.html).

A BEV traction motor is not a traction battery. Battery collection efficiencies and lithium, cobalt, nickel or lead recovery targets must therefore not be transferred to NdFeB magnets, copper windings or motor housings. The Battery Regulation can influence the wider vehicle reverse-logistics system and may improve the economic context for authorised treatment, but it does not establish a motor-magnet recovery TC.

### 8.4 Regulatory implication for 2030 and 2060

Regulation can improve four upstream conditions:

1. identification of magnet-bearing products;
2. removal before destructive treatment;
3. access to composition and dismantling information;
4. investment certainty for recycling capacity.

The physical TC still depends on implementation, enforcement, design, process operation and market outlets. Auditable monitoring should report masses at each boundary rather than only compliance declarations.

## 9 Gaps and Data Uncertainties

### 9.1 Absence of fleet-wide routing statistics

No supplied source reports what fraction of end-of-life BEV motors is reused, exported, stored, shredded, manually dismantled or sent to specialist magnet recycling. This is the largest uncertainty in the upstream chain. Statements about the “current route” are therefore descriptions of known practices, not a measured market split.

### 9.2 Boundary inconsistency

Studies variously begin with:

- an end-of-life vehicle;
- a removed drive unit;
- a motor;
- a rotor;
- extracted magnets;
- manufacturing scrap;
- clean magnet powder.

Their reported recovery values cannot be compared without boundary conversion. A 99% leaching yield from clean powder may coexist with a much lower vehicle-to-product recovery if capture and extraction are poor.

### 9.3 Concentration versus recovery

Enrichment to 50.8% NdFeB is useful because it improves downstream feed quality, but it is not a recovery rate [[10]](https://doi.org/10.1177/0734242x261476422) [[11]](https://pubmed.ncbi.nlm.nih.gov/42625283/) [[12]](https://chemrxiv.org/engage/chemrxiv/article-details/6721e7215a82cea2fa4debeb). Studies should publish:

- feed mass and composition;
- every output-stream mass;
- NdFeB or elemental concentration in each stream;
- analytical uncertainty;
- residues and unaccounted mass.

### 9.4 Element-specific partitioning

Many studies report “rare earths,” “NdPr,” “magnet alloy” or only Nd. Dy and Tb may partition differently in roasting, slagging, leaching or separation. Assigning a common coefficient to Nd, Pr, Dy and Tb is acceptable only as an explicitly labelled proxy before element-selective operations.

### 9.5 Magnet chemistry and ageing

NdFeB grades differ in Nd/Pr ratio, heavy-rare-earth content, cobalt and other additions, coatings and grain-boundary treatments. The reference motor’s Dy and Tb ranges are particularly broad [1] [2]. Service ageing, corrosion and thermal exposure add uncertainty.

### 9.6 Ambiguous architecture and component data

The supplied RAWCLIC spreadsheet contains entries labelled as EESM rotor windings under a rare-earth material category even though EESM is magnet-free [4]. This appears to be a classification or material-key inconsistency and should not be interpreted as evidence that EESM rotor windings are rare-earth magnets. Dataset validation should distinguish copper rotor winding from rare-earth material.

### 9.7 Automation evidence

Robot-assisted dismantling is demonstrated, but cycle time, availability, tool change, fault recovery and unit cost are rarely published. Laboratory success on one motor family cannot establish readiness for a mixed fleet [[15]](https://link.springer.com/chapter/10.1007/978-3-031-47394-4_45) [[6]](https://link.springer.com/chapter/10.1007/978-3-031-84744-8_6) [[7]](https://www.sciencedirect.com/science/article/pii/S2212827125003786) [[9]](https://www.iwks.fraunhofer.de/en/competencies/zdr-emil.html).

### 9.8 Commercial confidentiality

Recyclers often disclose capacity, purity or headline recovery but not complete mass balances, reject rates, reagent consumption, product qualification or allocation of internal recycle. Commercial claims remain useful evidence of activity, but they do not support 100% reliability.

### 9.9 Energy data

Compatible kWh/kg values are unavailable for:

- motor dehousing;
- thermal demagnetisation;
- HPMS treatment;
- HDDR;
- motor-specific hydrometallurgy;
- combined pyro-hydrometallurgical treatment.

Energy is therefore NR. Future studies should separate electricity, fuel, hydrogen, thermal energy and embodied reagent energy.

### 9.10 Long-horizon uncertainty

A 2060 scenario depends on technologies, motor designs, regulations and markets extending beyond the demonstrated evidence. It should be used for sensitivity analysis, not as a point forecast. Architecture change may reduce magnet-bearing motor share; improved magnet design may reduce Dy and Tb content; axial-flux adoption may sustain demand. These effects influence available feedstock as well as recycling technology.

### 9.11 Priority data programme

An audit-ready demonstration should process a statistically documented batch of complete removed motors and publish:

1. motor architecture and mass;
2. initial NdFeB, Nd, Pr, Dy and Tb inventory;
3. time and energy for dehousing;
4. mass and composition of housing, stator, rotor and residues;
5. magnet extraction yield;
6. process-stage recovery;
7. purification yield;
8. oxide, metal, alloy or magnet product mass;
9. product specification and rejection;
10. uncertainty and closure of the material balance.

Without these data, the full-chain TC will remain a scenario parameter rather than a measurement.

## 10 Conclusions

BEV traction-motor recycling is best understood as a routing problem linking vehicle treatment, motor disassembly, magnet liberation and metallurgical processing. High chemical recovery at the end of the chain cannot compensate for a motor that is not captured or a magnet that is dispersed into an unsuitable scrap stream.

The motor-unit-removal boundary is appropriate for detailed process modelling, provided that EoL capture and motor removal remain explicit upstream multipliers. Only PMSMs and permanent-magnet axial-flux machines enter the NdFeB recycling chain. ASM/IM and EESM are magnet-free, although they remain important copper, aluminium and steel sources.

For a nominal 150 kW PMSM, the appropriate planning inventory is 1.0 | 1.5 | 2.0 kg NdFeB, containing 0.25 | 0.38 | 0.55 kg Nd, 0.03 | 0.08 | 0.15 kg Pr, 0.01 | 0.05 | 0.12 kg Dy and 0.00 | 0.01 | 0.03 kg Tb [1] [2]. These ranges are not a substitute for product-specific data.

Current industrial practice is mixed. Legacy shredding remains important for bulk metals, while selective motor disassembly, thermal demagnetisation, controlled fragmentation and hydrogen-assisted extraction are being demonstrated and scaled. The evidence does not show that all current motors are shredded, and it does not support a universal near-zero NdFeB recovery coefficient for shredding.

Selective disassembly gives the best access to intact magnets and short-loop recycling, but manual work is costly and flexible automation remains at pilot or demonstration level. Controlled shredding after demagnetisation can produce a concentrated magnet fraction, but concentration alone does not establish recovery.

Direct reuse offers the highest value retention but lacks representative public yields. HD and HPMS are the strongest short-loop candidates for 2030 and have progressed toward early commercial deployment. HDDR and direct powder routes remain important specialised options. Hydrometallurgy is the principal long-loop route for purified rare-earth products, while pyrometallurgy can treat heterogeneous feed and concentrate rare earths for downstream processing.

The literature does not provide a complete, compatible set of TCs for 2030 or 2060. Unsupported values have therefore been reported as NR. This is a substantive result: using a laboratory leaching yield, commercial purity claim or regulatory target as a complete recycling rate would materially overstate circular supply.

The likely 2030 system is a portfolio combining motor removal, selective dismantling, hydrogen-based short-loop recycling, hydrometallurgical treatment of mixed feed and controlled mechanical concentration. The 2060 case is a scenario, not a forecast. Its most credible form is an information-rich cascade that routes motors and magnets according to condition, chemistry and contamination.

For RAWCLIC modelling, the recommended approach is to:

- preserve every process boundary;
- maintain separate disassembly and shredding branches;
- model Nd, Pr, Dy and Tb separately only when the evidence supports it;
- retain an explicit unknown-fate stream;
- distinguish material recycling from functional closed-loop recycling;
- identify every non-measured 2030 or 2060 value as a scenario assumption;
- update the coefficients when audited industrial mass balances become available.

## 11 References

[3] Anspach, R., Rösslein, M., Boga, B., Feldmann, L., Desing, H. and Remmen, K. *BEV Traction Motor Composition Data: Deliverable 3.1—Harmonized Datasets for Secondary RM Sources for the Twin Transition*. RAWCLIC, 2026. [Reliability: 100%]

[1] Roesslein, M. *Practical BEV Traction-Motor Architecture, Weight and Materials Outlook*. 2026. [Reliability: 100%]

[2] Roesslein, M. *BEV Motors Practical Data v2*. 2026. [Reliability: 100%]

[4] RAWCLIC. *BEV Motor Consolidated Data V1*. 2026. [Reliability: 100%]

[[77]](https://www.sciencedirect.com/science/article/pii/S0306261923018603) ScienceDirect literature on electric-vehicle motor development and circularity. [Reliability: 100%]

[[71]](https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:52025DC0260) EUR-Lex, EU battery-law source. [Reliability: 100%]

[[72]](https://eur-lex.europa.eu/EN/legal-content/summary/deployment-of-alternative-fuels-infrastructure.html) EUR-Lex, Regulation (EU) 2023/1542 documentation. [Reliability: 100%]

[[73]](https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX%3A42023X0401) EUR-Lex, EU battery regulatory text. [Reliability: 100%]

[[74]](https://eur-lex.europa.eu/eli/dir/2006/126/2020-11-01/eng) EUR-Lex, battery and vehicle regulatory documentation. [Reliability: 100%]

[[75]](https://eur-lex.europa.eu/EN/legal-content/summary/road-safety-driving-licences.html) EUR-Lex, EU regulatory source. [Reliability: 100%]

[[76]](https://eur-lex.europa.eu/EN/legal-content/summary/two-or-three-wheeled-motor-vehicles-maximum-design-speed.html) EUR-Lex, EU battery-law source. [Reliability: 100%]

[[65]](https://publications.jrc.ec.europa.eu/repository/bitstream/JRC140892/JRC140892_01.pdf) Joint Research Centre publication on critical raw materials and permanent magnets. [Reliability: 100%]

[[78]](https://publications.jrc.ec.europa.eu/repository/bitstream/JRC122671/jrc122671_the_role_of_rare_earth_elements_in_wind_energy_and_electric_mobility_2.pdf) Joint Research Centre publication on rare-earth supply and recycling. [Reliability: 100%]

[[5]](https://joint-research-centre.ec.europa.eu/jrc-news-and-updates/innovative-requirements-could-boost-circular-economy-plastics-and-critical-raw-materials-vehicles-2023-07-13_en) Joint Research Centre evidence on end-of-life vehicles and material circularity. [Reliability: 100%]

[[79]](https://single-market-economy.ec.europa.eu/sectors/raw-materials/areas-specific-interest/rare-earth-elements-permanent-magnets-and-motors_en) European Commission single-market evidence on the rare-earth magnet value chain. [Reliability: 100%]

[[47]](https://www.mdpi.com/2075-4701/14/6/658) Peer-reviewed review of NdFeB recycling and demagnetisation routes. [Reliability: 100%]

[[80]](https://link.springer.com/article/10.1007/s11837-023-06235-1) Peer-reviewed Springer literature on rare-earth recycling and circularity. [Reliability: 100%]

[[48]](https://www.sciencedirect.com/science/article/abs/pii/S2452223624000051) Peer-reviewed literature on thermal treatment and NdFeB recycling. [Reliability: 100%]

[[14]](https://www.sciencedirect.com/science/article/pii/S0921344924001769) Peer-reviewed study of functional disassembly and direct recycling of permanent-magnet motors. [Reliability: 100%]

[[81]](https://www.sciencedirect.com/science/article/pii/S2212827126006104) Peer-reviewed decision framework for end-of-life electromechanical components. [Reliability: 100%]

[[82]](https://www.eit.europa.eu/sites/default/files/2021_09-24_ree_cluster_report2.pdf) EIT/EU material on rare-earth magnets and European supply security. [Reliability: 100%]

[[26]](https://pubs.acs.org/acsodf/article/8/20/17431/407376/Review-on-the-Parameters-of-Recycling-NdFeB) Peer-reviewed ACS literature on hydrogen processing of NdFeB. [Reliability: 100%]

[[52]](https://www.mdpi.com/2075-4701/15/11/1227) Peer-reviewed review of direct NdFeB recycling. [Reliability: 100%]

[[27]](https://pmc.ncbi.nlm.nih.gov/articles/PMC12897740/) Peer-reviewed literature on hydrogen-based magnet recycling. [Reliability: 100%]

[[28]](https://research.birmingham.ac.uk/en/publications/recycling-of-ndfeb-magnets-from-hard-disc-drive-scrap-using-hpms-/) University of Birmingham research on hydrogen processing of magnet scrap. [Reliability: 100%]

[[29]](https://link.springer.com/article/10.1007/s10163-025-02162-2) Peer-reviewed Springer literature on NdFeB powder recycling. [Reliability: 100%]

[[53]](https://www.mdpi.com/2071-1050/13/17/9668) Peer-reviewed review of permanent-magnet recycling methods. [Reliability: 100%]

[[30]](https://onlinelibrary.wiley.com/doi/10.1155/2014/638013) Peer-reviewed Wiley literature on HDDR and recycled magnet powders. [Reliability: 100%]

[[51]](https://iopscience.iop.org/article/10.1088/1361-6668/ad54f5) Peer-reviewed IOP literature on NdFeB recycling. [Reliability: 100%]

[[54]](https://www.mdpi.com/1996-1073/11/4/792) Peer-reviewed review of functional rare-earth magnet recycling. [Reliability: 100%]

[[10]](https://doi.org/10.1177/0734242x261476422) Peer-reviewed research on thermal demagnetisation, shredding and NdFeB separation. [Reliability: 100%]

[[11]](https://pubmed.ncbi.nlm.nih.gov/42625283/) Peer-reviewed evidence on magnet enrichment through mechanical treatment. [Reliability: 100%]

[[17]](https://www.sciencedirect.com/science/article/pii/S2214993725055123) Peer-reviewed research on hydrogen and metallurgical recovery of NdFeB. [Reliability: 100%]

[[31]](https://www.mdpi.com/2227-9717/13/6/1729) Peer-reviewed study of integrated motor recycling, smelting and hydrometallurgical recovery. [Reliability: 100%]

[[49]](https://link.springer.com/chapter/10.1007/978-3-032-21154-5_22) Peer-reviewed Springer literature on functional magnet recycling. [Reliability: 100%]

[[50]](https://www.researchgate.net/publication/389513583_Functional_Recycling_and_Reuse_of_Nd-Fe-B_Permanent_Magnets_from_Various_Waste_Streams_for_a_more_Sustainable_and_Resilient_Electromobility) Research literature on functional recycling of traction-motor magnets. [Reliability: 40%]

[[32]](https://pubs.rsc.org/en/content/articlehtml/2025/cc/d4cc04252b) Peer-reviewed Royal Society of Chemistry literature on electrochemical and metallurgical rare-earth recovery. [Reliability: 100%]

[[43]](https://link.springer.com/article/10.1007/s13243-024-00143-6) Peer-reviewed Springer review of permanent-magnet demagnetisation and recycling. [Reliability: 100%]

[[44]](https://link.springer.com/article/10.1007/s40831-016-0090-4) Peer-reviewed literature on disassembly and collection constraints for EV magnets. [Reliability: 100%]

[[83]](https://link.springer.com/article/10.1007/s40831-016-0085-1) Peer-reviewed Springer literature on mechanical pretreatment of magnet-bearing motors. [Reliability: 100%]

[[33]](https://www.okonrecycling.com/magnet-recycling-and-applications/magnet-technology/ev-motor-magnet-recovery/) Recycler technical overview of rare-earth magnet recycling. [Reliability: 60%]

[[45]](https://www.mdpi.com/2673-4591/131/1/11) Peer-reviewed review of magnet identification and recycling systems. [Reliability: 100%]

[[34]](https://www.reecycleinc.com/recycle-electric-motor-magnets) REEcycle technical and commercial recovery claim. [Reliability: 60%]

[[46]](https://pmc.ncbi.nlm.nih.gov/articles/PMC11985978/) Peer-reviewed evidence on automated motor and magnet identification. [Reliability: 100%]

[[15]](https://link.springer.com/chapter/10.1007/978-3-031-47394-4_45) Peer-reviewed research on flexible magnet-disassembly cells. [Reliability: 100%]

[[18]](https://www.fastmarkets.com/insights/rare-earth-magnet-recycling-technology-branches-out/) Established specialist-market reporting on magnet-recycling scale-up. [Reliability: 80%]

[[19]](https://www.okonrecycling.com/magnet-recycling-and-applications/magnet-technology/rare-earth-motor-magnet-recycling/) Recycler technical discussion of motor disassembly and rare-earth recovery. [Reliability: 60%]

[[6]](https://link.springer.com/chapter/10.1007/978-3-031-84744-8_6) Peer-reviewed research on automated magnet disassembly. [Reliability: 100%]

[[12]](https://chemrxiv.org/engage/chemrxiv/article-details/6721e7215a82cea2fa4debeb) Unreviewed technical research on thermal demagnetisation and mechanical concentration. [Reliability: 40%]

[[16]](https://www.sciencedirect.com/science/article/pii/S2214993725003549) Peer-reviewed study of debonding and disassembly-time reduction. [Reliability: 100%]

[[7]](https://www.sciencedirect.com/science/article/pii/S2212827125003786) Peer-reviewed research on human–robot cooperative motor disassembly. [Reliability: 100%]

[[13]](https://link.springer.com/article/10.1007/s12649-026-03754-1) Peer-reviewed literature on mechanical enrichment of NdFeB motor scrap. [Reliability: 100%]

[[59]](https://link.springer.com/article/10.1007/s40831-018-0198-9) Peer-reviewed Springer literature on motor-magnet demagnetisation and molten-salt recovery. [Reliability: 100%]

[[58]](https://link.springer.com/chapter/10.1007/978-3-031-81182-1_5) Peer-reviewed research on liquid-magnesium extraction of rare earths. [Reliability: 100%]

[[8]](https://www.fraunhofer.de/en/press/research-news/2024/january-2024/electromobility-second-life-for-electric-motors.html) Fraunhofer REASSERT research on reuse, repair, remanufacturing and recycling of electric motors. [Reliability: 80%]

[[55]](https://www.ifam.fraunhofer.de/en/Aboutus/Locations/Dresden/HydrogenTechnology/recycling.html) Fraunhofer IFAM research on hydrometallurgical rare-earth recovery. [Reliability: 80%]

[[56]](https://www.igb.fraunhofer.de/en/reference-projects/fraunhofer-lighthouse-project-critical-rare-earths.html) Fraunhofer research on rare-earth recycling and process development. [Reliability: 80%]

[[20]](https://www.iwks.fraunhofer.de/en/competencies/MagneticMaterials/Recycling.html) Fraunhofer research on hydrogen processing of permanent magnets. [Reliability: 80%]

[[57]](https://www.materials.fraunhofer.de/en/business-areas/energy_and_environment/recycling-of-rare-eart-magnets.html) Fraunhofer research on selective chemical recovery of Nd, Pr and Dy. [Reliability: 80%]

[[21]](https://www.iwks.fraunhofer.de/en/projects/current-projects/recyper.html) Fraunhofer RecyPer work on recycled magnetic material. [Reliability: 80%]

[[9]](https://www.iwks.fraunhofer.de/en/competencies/zdr-emil.html) Fraunhofer ZDR-EMIL work on automated dismantling and recycling for electromobility. [Reliability: 80%]

[[66]](https://op.europa.eu/en/publication-detail/-/publication/34274068-ee70-11ef-b5e9-01aa75ed71a1/language-en) EU publication on permanent-magnet information and circularity requirements. [Reliability: 100%]

[[60]](https://cordis.europa.eu/article/id/413346-designing-and-recycling-electric-motors) CORDIS, DEMETER project documentation. [Reliability: 100%]

[[61]](https://cordis.europa.eu/docs/results/310/310240/final1-remanence-final-report-v1.pdf) CORDIS, REMANENCE project documentation. [Reliability: 100%]

[[84]](https://cinea.ec.europa.eu/news-events/news/life-inspiree-mining-valuable-metals-our-waste-large-scale-2025-04-28_en) European Climate, Infrastructure and Environment Executive Agency, LIFE INSPIREE project documentation. [Reliability: 100%]

[[22]](https://rare-earth-mining.com/hypromag/) Supplier and sector reporting on HyProMag’s hydrogen-processing route. [Reliability: 60%]

[[23]](https://hypromagusa.com/technology/) HyProMag USA technical description of HPMS. [Reliability: 60%]

[[24]](https://hypromag.com/executive-summary-of-recent-technical-progress-by-hypromag-ltd-june-2025/) HyProMag technical information on magnet recycling. [Reliability: 60%]

[[25]](https://hypromag.com/about/) HyProMag facility and process information. [Reliability: 60%]

[[35]](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:52023PC0451) EUR-Lex, Regulation (EU) 2024/1252, Critical Raw Materials Act. [Reliability: 100%]

[[36]](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=legissum%3Al21225) EUR-Lex documentation supporting Regulation (EU) 2024/1252. [Reliability: 100%]

[[63]](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=COM%3A2023%3A451%3AFIN&qid=1689318552193) EUR-Lex, Critical Raw Materials Act legislative documentation. [Reliability: 100%]

[[64]](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=LEGISSUM:l21225) EUR-Lex, strategic raw-material legal framework. [Reliability: 100%]

[[37]](https://ec.europa.eu/eurostat/statistics-explained/index.php?title=End-of-life_vehicle_statistics) European Commission documentation on the Critical Raw Materials Act. [Reliability: 100%]

[[38]](https://environment.ec.europa.eu/topics/waste-and-recycling/end-life-vehicles/end-life-vehicles-regulation_en) European Commission environment documentation on end-of-life vehicles. [Reliability: 100%]

[[67]](https://environment.ec.europa.eu/topics/waste-and-recycling/end-life-vehicles_en) European Commission documentation on proposed ELV changes. [Reliability: 100%]

[[62]](https://rmis.jrc.ec.europa.eu/uploads/CRMs_for_Strategic_Technologies_and_Sectors_in_the_EU_2020.pdf) JRC Raw Materials Information System documentation. [Reliability: 100%]

[[39]](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex:52023PC0451) EUR-Lex, enacted Critical Raw Materials Act text. [Reliability: 100%]

[[40]](https://eur-lex.europa.eu/procedure/EN/2023_284) EUR-Lex, Critical Raw Materials Act implementation framework. [Reliability: 100%]

[[68]](https://ec.europa.eu/environment/pdf/waste/elv/ELV_report.pdf) European Commission documentation on vehicle circularity. [Reliability: 100%]

[[69]](https://ec.europa.eu/eurostat/statistics-explained/index.php?title=End-of-life_vehicle_statistics&oldid=545041) European Commission documentation on end-of-life vehicle policy. [Reliability: 100%]

[[70]](https://ec.europa.eu/environment/pdf/waste/studies/elv/compliance_art7_2.pdf) European Commission documentation on vehicle design and recycling proposals. [Reliability: 100%]

[[41]](https://eur-lex.europa.eu/legal-content/EN/HTML/?uri=OJ:L_202401252) EUR-Lex documentation relevant to batteries and circularity. [Reliability: 100%]

[[42]](https://eur-lex.europa.eu/legal-content/LIT/TXT/?uri=CELEX%3A32024R1252) EUR-Lex documentation on the EU battery framework. [Reliability: 100%]

---

## References

1. BEV_Motors_Practical_Report_v2.md (uploaded document)
2. BEV_Motors_Practical_Data_v2.xlsx (uploaded document)
3. RAWCLIC_BEV_motor_consolidated_data_description-V1.pdf (uploaded document)
4. RAWCLIC_BEV_motor_consolidated_data_V1.xlsx (uploaded document)
5. <https://joint-research-centre.ec.europa.eu/jrc-news-and-updates/innovative-requirements-could-boost-circular-economy-plastics-and-critical-raw-materials-vehicles-2023-07-13_en>
6. <https://link.springer.com/chapter/10.1007/978-3-031-84744-8_6>
7. <https://www.sciencedirect.com/science/article/pii/S2212827125003786>
8. <https://www.fraunhofer.de/en/press/research-news/2024/january-2024/electromobility-second-life-for-electric-motors.html>
9. <https://www.iwks.fraunhofer.de/en/competencies/zdr-emil.html>
10. <https://doi.org/10.1177/0734242x261476422>
11. <https://pubmed.ncbi.nlm.nih.gov/42625283/>
12. <https://chemrxiv.org/engage/chemrxiv/article-details/6721e7215a82cea2fa4debeb>
13. <https://link.springer.com/article/10.1007/s12649-026-03754-1>
14. <https://www.sciencedirect.com/science/article/pii/S0921344924001769>
15. <https://link.springer.com/chapter/10.1007/978-3-031-47394-4_45>
16. <https://www.sciencedirect.com/science/article/pii/S2214993725003549>
17. <https://www.sciencedirect.com/science/article/pii/S2214993725055123>
18. <https://www.fastmarkets.com/insights/rare-earth-magnet-recycling-technology-branches-out/>
19. <https://www.okonrecycling.com/magnet-recycling-and-applications/magnet-technology/rare-earth-motor-magnet-recycling/>
20. <https://www.iwks.fraunhofer.de/en/competencies/MagneticMaterials/Recycling.html>
21. <https://www.iwks.fraunhofer.de/en/projects/current-projects/recyper.html>
22. <https://rare-earth-mining.com/hypromag/>
23. <https://hypromagusa.com/technology/>
24. <https://hypromag.com/executive-summary-of-recent-technical-progress-by-hypromag-ltd-june-2025/>
25. <https://hypromag.com/about/>
26. <https://pubs.acs.org/acsodf/article/8/20/17431/407376/Review-on-the-Parameters-of-Recycling-NdFeB>
27. <https://pmc.ncbi.nlm.nih.gov/articles/PMC12897740/>
28. <https://research.birmingham.ac.uk/en/publications/recycling-of-ndfeb-magnets-from-hard-disc-drive-scrap-using-hpms-/>
29. <https://link.springer.com/article/10.1007/s10163-025-02162-2>
30. <https://onlinelibrary.wiley.com/doi/10.1155/2014/638013>
31. <https://www.mdpi.com/2227-9717/13/6/1729>
32. <https://pubs.rsc.org/en/content/articlehtml/2025/cc/d4cc04252b>
33. <https://www.okonrecycling.com/magnet-recycling-and-applications/magnet-technology/ev-motor-magnet-recovery/>
34. <https://www.reecycleinc.com/recycle-electric-motor-magnets>
35. <https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:52023PC0451>
36. <https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=legissum%3Al21225>
37. <https://ec.europa.eu/eurostat/statistics-explained/index.php?title=End-of-life_vehicle_statistics>
38. <https://environment.ec.europa.eu/topics/waste-and-recycling/end-life-vehicles/end-life-vehicles-regulation_en>
39. <https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex:52023PC0451>
40. <https://eur-lex.europa.eu/procedure/EN/2023_284>
41. <https://eur-lex.europa.eu/legal-content/EN/HTML/?uri=OJ:L_202401252>
42. <https://eur-lex.europa.eu/legal-content/LIT/TXT/?uri=CELEX%3A32024R1252>
43. <https://link.springer.com/article/10.1007/s13243-024-00143-6>
44. <https://link.springer.com/article/10.1007/s40831-016-0090-4>
45. <https://www.mdpi.com/2673-4591/131/1/11>
46. <https://pmc.ncbi.nlm.nih.gov/articles/PMC11985978/>
47. <https://www.mdpi.com/2075-4701/14/6/658>
48. <https://www.sciencedirect.com/science/article/abs/pii/S2452223624000051>
49. <https://link.springer.com/chapter/10.1007/978-3-032-21154-5_22>
50. <https://www.researchgate.net/publication/389513583_Functional_Recycling_and_Reuse_of_Nd-Fe-B_Permanent_Magnets_from_Various_Waste_Streams_for_a_more_Sustainable_and_Resilient_Electromobility>
51. <https://iopscience.iop.org/article/10.1088/1361-6668/ad54f5>
52. <https://www.mdpi.com/2075-4701/15/11/1227>
53. <https://www.mdpi.com/2071-1050/13/17/9668>
54. <https://www.mdpi.com/1996-1073/11/4/792>
55. <https://www.ifam.fraunhofer.de/en/Aboutus/Locations/Dresden/HydrogenTechnology/recycling.html>
56. <https://www.igb.fraunhofer.de/en/reference-projects/fraunhofer-lighthouse-project-critical-rare-earths.html>
57. <https://www.materials.fraunhofer.de/en/business-areas/energy_and_environment/recycling-of-rare-eart-magnets.html>
58. <https://link.springer.com/chapter/10.1007/978-3-031-81182-1_5>
59. <https://link.springer.com/article/10.1007/s40831-018-0198-9>
60. <https://cordis.europa.eu/article/id/413346-designing-and-recycling-electric-motors>
61. <https://cordis.europa.eu/docs/results/310/310240/final1-remanence-final-report-v1.pdf>
62. <https://rmis.jrc.ec.europa.eu/uploads/CRMs_for_Strategic_Technologies_and_Sectors_in_the_EU_2020.pdf>
63. <https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=COM%3A2023%3A451%3AFIN&qid=1689318552193>
64. <https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=LEGISSUM:l21225>
65. <https://publications.jrc.ec.europa.eu/repository/bitstream/JRC140892/JRC140892_01.pdf>
66. <https://op.europa.eu/en/publication-detail/-/publication/34274068-ee70-11ef-b5e9-01aa75ed71a1/language-en>
67. <https://environment.ec.europa.eu/topics/waste-and-recycling/end-life-vehicles_en>
68. <https://ec.europa.eu/environment/pdf/waste/elv/ELV_report.pdf>
69. <https://ec.europa.eu/eurostat/statistics-explained/index.php?title=End-of-life_vehicle_statistics&oldid=545041>
70. <https://ec.europa.eu/environment/pdf/waste/studies/elv/compliance_art7_2.pdf>
71. <https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:52025DC0260>
72. <https://eur-lex.europa.eu/EN/legal-content/summary/deployment-of-alternative-fuels-infrastructure.html>
73. <https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX%3A42023X0401>
74. <https://eur-lex.europa.eu/eli/dir/2006/126/2020-11-01/eng>
75. <https://eur-lex.europa.eu/EN/legal-content/summary/road-safety-driving-licences.html>
76. <https://eur-lex.europa.eu/EN/legal-content/summary/two-or-three-wheeled-motor-vehicles-maximum-design-speed.html>
77. <https://www.sciencedirect.com/science/article/pii/S0306261923018603>
78. <https://publications.jrc.ec.europa.eu/repository/bitstream/JRC122671/jrc122671_the_role_of_rare_earth_elements_in_wind_energy_and_electric_mobility_2.pdf>
79. <https://single-market-economy.ec.europa.eu/sectors/raw-materials/areas-specific-interest/rare-earth-elements-permanent-magnets-and-motors_en>
80. <https://link.springer.com/article/10.1007/s11837-023-06235-1>
81. <https://www.sciencedirect.com/science/article/pii/S2212827126006104>
82. <https://www.eit.europa.eu/sites/default/files/2021_09-24_ree_cluster_report2.pdf>
83. <https://link.springer.com/article/10.1007/s40831-016-0085-1>
84. <https://cinea.ec.europa.eu/news-events/news/life-inspiree-mining-valuable-metals-our-waste-large-scale-2025-04-28_en>
