# Battery Cell Recycling for LFP, LMFP and NMC: Technical Performance, Scenarios and EU Compliance
*Matthias Roesslein — September 15, 2026*

## Executive summary

### Decision in brief

Battery recycling strategy should be chemistry-specific at the front end and product-specific at the back end:

1. **NMC is best served in the near term by mechanical pretreatment followed by hydrometallurgy or a combined pyro-hydrometallurgical route.** These routes have the strongest industrial and experimental evidence for recovering lithium, nickel, cobalt and manganese. Pyrometallurgy remains robust for heterogeneous feeds and concentrates nickel and cobalt into an alloy, but conventional smelting does not by itself demonstrate strong lithium recovery; lithium usually requires subsequent slag refining or another specialized step [[1]](https://publications.jrc.ec.europa.eu/repository/handle/JRC129861) [[2]](https://pubs.rsc.org/en/content/articlehtml/2023/su/d3su00142c).

2. **LFP should not be treated as low-grade NMC feed by default.** Dedicated selective hydrometallurgy can extract lithium while retaining iron and phosphorus together as an iron-phosphate residue or precursor. Direct regeneration may preserve more cathode value and reduce processing burdens, but it requires substantially cleaner, chemistry-controlled feed than elemental recovery. The commercial challenge is primarily economic rather than a lack of laboratory-scale technical options [[3]](https://www.mdpi.com/2313-0105/11/1/33) [[4]](https://www.oaepublish.com/articles/energymater.2023.57) [[5]](https://pubmed.ncbi.nlm.nih.gov/41946108/).

3. **LMFP should be managed as an LFP-family chemistry containing intrinsic manganese, not as either ordinary LFP or NMC.** Direct end-of-life LMFP evidence remains sparse. One chemistry-specific hydrometallurgical study reports near-complete leaching under optimized conditions and proposes sequential recovery of iron, manganese and lithium phosphates, but the evidence base is too narrow to establish industrial whole-cell transfer coefficients [[6]](https://www.sciencedirect.com/science/article/abs/pii/S221499372300060X). Direct upcycling of spent LFP into LMFP demonstrates a potentially valuable pathway, but it is not evidence for recycling spent LMFP cells [[7]](https://pmc.ncbi.nlm.nih.gov/articles/PMC13224291/) [[8]](https://pubs.rsc.org/en/content/articlehtml/2026/sc/d6sc03686d).

4. **Do not equate a leaching percentage with a whole-cell recovery or transfer coefficient.** A result such as 98% lithium leaching describes transfer from the tested cathode powder into solution under specified laboratory conditions. It does not include collection losses, pack dismantling, black-mass production, filtration, purification, precipitation, product rejection or residues. Decision-grade mass balances must distinguish:
   - release or leaching into an intermediate stream;
   - retention in a solid precursor;
   - yield into a saleable recovered product;
   - elemental material recovery under EU methodology; and
   - whole-battery recycling efficiency by mass.

5. **The binding EU requirements are process and element metrics, not chemistry-specific forecasts.** For lithium-based waste batteries, recycling efficiency must be at least **65% by 31 December 2025** and **70% by 31 December 2030**. Material recovery must reach **50% for lithium by 31 December 2027 and 80% by 31 December 2031**. Cobalt and nickel—along with copper and lead—must reach **90% by 31 December 2027 and 95% by 31 December 2031** [[9]](https://environment.ec.europa.eu/news/new-rules-boost-recycling-efficiency-waste-batteries-2025-07-04_en) [[10]](https://eur-lex.europa.eu/EN/legal-content/summary/sustainability-rules-for-batteries-and-waste-batteries.html) [[11]](https://eur-lex.europa.eu/legal-content/uk/LSU/?uri=CELEX%3A32023R1542). These requirements do not create corresponding recovery targets for manganese, iron or phosphorus.

6. **Commission Delegated Regulation (EU) 2025/606 is the controlling calculation framework for recycling efficiency and material recovery.** It entered into application in July 2025 and prescribes calculation, verification and harmonized documentation rules [[9]](https://environment.ec.europa.eu/news/new-rules-boost-recycling-efficiency-waste-batteries-2025-07-04_en) [[12]](https://revivebatts.com/battery-recycling-efficiency-eu-2026/). Temporary methodological flexibility affecting substances including graphite, iron and phosphorus runs through the end of 2029; it should not be interpreted as evidence that those materials are physically recovered or that they may be ignored after 2030 [[13]](https://environment.ec.europa.eu/document/download/6297f987-49f6-432b-8119-d60fb6a26c9b_en?filename=COM_2026_470_1_EN_ACT_part1_v3.pdf).

### Headline scenario results

The scenarios in this report are **analyst scenarios**, not measured plant guarantees or legal targets. They represent conditional transfer from an element entering the main recycling operation to a qualifying recovered output. They therefore exclude collection unless otherwise stated.

| Chemistry | Intrinsic target elements | 2030 mode scenario | 2050 mode scenario | 2060 mode scenario | Decision implication |
|---|---|---:|---:|---:|---|
| LFP | Li, Fe, P | Li 85%; Fe 85%; P 80% | Li 94%; Fe 92%; P 90% | Li 96%; Fe 94%; P 93% | Contract separately for lithium product and Fe–P residue valorization; otherwise headline lithium performance can coexist with poor full-element circularity. |
| LMFP | Li, Mn, Fe, P | Li 82%; Mn 80%; Fe 78%; P 75% | Li 92%; Mn 90%; Fe 88%; P 86% | Li 95%; Mn 93%; Fe 91%; P 90% | Require chemistry identification and a manganese mass balance. LFP analogues alone are insufficient for qualification. |
| NMC | Li, Ni, Co, Mn | Li 85%; Ni 95%; Co 95%; Mn 90% | Li 94%; Ni 98%; Co 98%; Mn 96% | Li 97%; Ni 99%; Co 99%; Mn 98% | Near-term procurement should prioritize verified product recovery, especially for lithium and manganese, rather than relying on high Ni/Co leaching values. |

**Metric:** percentage of each intrinsic cathode element entering the main recycling operation that reaches a qualifying recovered material or regenerated cathode output. These are scenario assumptions informed by selective LFP leaching, LMFP laboratory research, NMC hydrometallurgical evidence, EU targets and technology-maturity literature [[4]](https://www.oaepublish.com/articles/energymater.2023.57) [[5]](https://pubmed.ncbi.nlm.nih.gov/41946108/) [[6]](https://www.sciencedirect.com/science/article/abs/pii/S221499372300060X) [[2]](https://pubs.rsc.org/en/content/articlehtml/2023/su/d3su00142c) [[14]](https://www.sciopen.com/local/article_pdf/10.1002/eem2.12863.pdf). Three independent chemistry-specific source groups do not exist for direct end-of-life LMFP or for 2060 process performance; those entries therefore use explicitly labelled LFP-family analogues and maturity assumptions rather than fabricated evidence.

### Principal risks

- **Boundary risk:** Recyclers may quote black-mass leaching efficiency while buyers assume pack-to-product recovery.
- **Feed risk:** Mixed LFP/NMC/LMFP streams can be chemically beneficial in reductive leaching but can also introduce phosphate, iron, aluminium and copper into the purification train [[15]](https://www.nature.com/articles/s41598-024-61569-3) [[16]](https://www.sciencedirect.com/science/article/pii/S0892687524004667).
- **Product risk:** High dissolution does not ensure battery-grade purity, saleable yield or cathode qualification.
- **Technology risk:** Direct regeneration is attractive but sensitive to chemistry mixing, ageing history and impurities.
- **Regulatory risk:** Compliance with whole-battery recycling efficiency does not automatically prove high recovery of every intrinsic cathode element.
- **Forecast risk:** Evidence becomes progressively weaker after 2031. Direct LMFP end-of-life evidence and all chemistry-specific 2060 projections are especially sparse.

## 1. Purpose, definitions and system boundary

### 1.1 Purpose

This report supports decisions by a battery or electric-vehicle operator selecting, contracting or auditing recycling routes for:

- lithium iron phosphate, or **LFP**;
- lithium manganese iron phosphate, or **LMFP**; and
- nickel-manganese-cobalt oxide, or **NMC**.

It evaluates process architecture, element fate, plausible future performance and EU legal obligations. It does not estimate recycling volumes, commodity prices or plant economics because the supplied evidence does not provide a consistent basis for those calculations.

### 1.2 Chemistry definitions

For this report:

- **LFP** is a phosphate cathode chemistry whose intentional cathode elements include lithium, iron and phosphorus.
- **LMFP** is an LFP-family phosphate chemistry in which manganese and iron are both intentional cathode constituents, together with lithium and phosphorus.
- **NMC** is a layered cathode family whose intentional cathode elements include lithium, nickel, manganese and cobalt.

Accordingly:

- nickel and cobalt are **not intrinsic LFP or LMFP constituents**;
- phosphorus and iron are **not intrinsic NMC cathode elements**;
- a non-intentional element is reported as **N/A**, not zero;
- traces caused by dopants, mixed feed, current collectors, casing or contamination do not change this chemistry classification.

Commercial LMFP may contain additional dopants, and mixed industrial black mass can contain elements from several cathode families. Such elements are impurities or stream constituents unless they form part of the declared cathode formulation.

### 1.3 System boundaries

Four boundaries are used because no single percentage adequately represents recycling performance.

| Boundary | Starting point | End point | Appropriate metric | Main exclusion |
|---|---|---|---|---|
| Laboratory reaction | Prepared cathode powder or black mass | Leachate or solid residue | Leaching, extraction or retention percentage | Collection, dismantling, most pretreatment and downstream product losses |
| Main-process transfer | Feed accepted into hydrometallurgical, pyrometallurgical or direct-regeneration operation | Qualifying recovered output | Element transfer coefficient | Upstream collection unless explicitly included |
| Plant recycling | Waste battery input at recycling plant | Countable recycled output fractions | EU recycling efficiency by mass | Collection before delivery |
| Circular-system performance | End-of-life batteries arising | Recovered material suitable for substitution | Collection-adjusted recovery | None within the defined regional system |

The core transfer coefficient used in this report is:

> **Element transfer coefficient:** mass of an element in a qualifying recovered product or regenerated cathode output divided by the mass of that element entering the main recycling operation.

A coefficient is destination-specific. Lithium entering a leachate is not yet recovered lithium carbonate. Iron and phosphorus retained together in solid FePO₄ may represent useful precursor retention if the residue is qualified for reuse, but not if it is discarded.

### 1.4 Metric distinctions

#### Experimentally measured leaching

A leaching percentage describes movement from a tested solid into solution. Examples include:

- 98.3% lithium leaching in an LFP oxidative route [[4]](https://www.oaepublish.com/articles/energymater.2023.57);
- 97.7% lithium leaching, with 1.26% iron and 16.15% phosphorus leaching, in another LFP experiment [[17]](https://www.sciencedirect.com/science/article/abs/pii/S2352152X24034182);
- approximately 96% lithium extraction with less than 0.1% iron and about 3% phosphorus dissolution in acetic-acid conditions [[5]](https://pubmed.ncbi.nlm.nih.gov/41946108/).

The low iron or phosphorus leaching values in these examples do not mean low recovery. They may instead indicate intentional retention of Fe and P in a solid FePO₄ phase.

#### Recovered-product yield

A recovered-product yield measures transfer into an isolated product, such as lithium carbonate, lithium phosphate, iron phosphate or a mixed NMC precursor. It is downstream of leaching and therefore usually lower than or equal to extraction, unless recycled process streams make the basis non-comparable.

The supplied evidence reports lithium carbonate purity up to 99.51% and demonstrates reuse of recovered FePO₄, but product purity is not the same metric as elemental yield [[18]](https://pmc.ncbi.nlm.nih.gov/articles/PMC10180280/).

#### Direct-regeneration yield

Direct recycling preserves and repairs cathode material rather than separating all elements. Its meaningful outputs are:

- mass yield of regenerated cathode;
- retention or replenishment of stoichiometry;
- impurity compliance;
- electrochemical qualification; and
- final product acceptance.

Elemental transfer can be high because Fe and P, or Ni, Mn and Co, remain within the solid. Nevertheless, lithium supplementation from an external source must not be misreported as recovered lithium.

#### Legal targets

EU recycling efficiency is a battery-level mass metric. EU material recovery is element-specific for cobalt, copper, lead, lithium and nickel. Neither is interchangeable with a laboratory extraction result [[9]](https://environment.ec.europa.eu/news/new-rules-boost-recycling-efficiency-waste-batteries-2025-07-04_en) [[12]](https://revivebatts.com/battery-recycling-efficiency-eu-2026/).

#### Analyst scenarios

The 2030, 2050 and 2060 values in this report are planning assumptions constructed from measured ranges, legal floors, route maturity and expected process integration. They are not forecasts issued by the cited sources.

## 2. Evidence ladder and scenario methodology

### 2.1 Evidence ladder

Evidence is weighted in the following order:

1. **Binding EU legislation and delegated regulations.**
2. **European Commission and JRC technical assessments.**
3. **Peer-reviewed experiments with explicit chemistry, conditions and outputs.**
4. **Peer-reviewed reviews synthesizing several routes.**
5. **Demonstration or pilot evidence with a stated material balance.**
6. **Analyst scenarios derived from levels 1–5.**
7. **Contextual secondary sources**, used only when official or peer-reviewed evidence in the supplied material does not contain a requested implementation detail.

High leaching efficiency from a single optimized experiment ranks below a complete product mass balance. A whole-cell industrial balance ranks above a cathode-powder experiment for procurement decisions, even if its nominal percentage is lower.

### 2.2 Construction of the process scenarios

The scenarios use three cases:

- **Minimum:** conservative but technically plausible performance, including pretreatment losses, imperfect purification and lower-value residue management.
- **Mode:** the most useful planning case for a competent operator using chemistry-appropriate processing.
- **Maximum:** high-performing, tightly controlled processing approaching the upper end of experimental evidence; it is not a routine guarantee.

The scenarios assume:

- material has arrived at the main recycling operation;
- declared chemistry is substantially correct;
- recovered outputs meet a defined substitution or reuse function;
- performance includes downstream separation, not only leaching;
- non-intrinsic elements are N/A;
- 2050 and 2060 improvements arise from maturation, better sorting, closed-loop purification and higher qualification rates rather than from a specific published forecast.

For 2030, the legal trajectory provides a reference point, but the table is not a restatement of law. In particular, the legally binding 80% lithium and 95% nickel/cobalt material-recovery requirements apply at the end of 2031, not at the end of 2030 [[9]](https://environment.ec.europa.eu/news/new-rules-boost-recycling-efficiency-waste-batteries-2025-07-04_en) [[11]](https://eur-lex.europa.eu/legal-content/uk/LSU/?uri=CELEX%3A32023R1542).

For 2050, external prospective evidence indicates that regional secondary-lithium supply depends strongly on battery lifetimes, collection and recovery, and that Europe could obtain a much larger recycled share than the global average under aggressive circularity conditions [[19]](https://doi.org/10.3390/recycling10040122). That evidence concerns supply contribution, not a chemistry-specific process coefficient.

For 2060, the supplied evidence contains no robust chemistry-specific process projections. The 2060 scenarios are therefore technology-maturity assumptions with wider epistemic uncertainty than their numerical range may suggest.

## 3. Recycling process architecture

### 3.1 Collection, diagnosis and sorting

The recycling chain begins before metallurgy. The owner must determine whether a battery is suitable for reuse, repurposing or recycling, then identify chemistry, state of charge and physical condition. The supplied JRC evidence identifies insufficient traceability, inconsistent pack design and lack of standardized usage-history information as barriers to automated disassembly and recycling [[1]](https://publications.jrc.ec.europa.eu/repository/handle/JRC129861).

Sorting has different value by route:

- pyro routes tolerate mixed chemistry more readily;
- hydro routes can accept mixed feeds but incur greater purification complexity;
- direct regeneration normally requires the narrowest chemistry and contamination window.

A recycler claiming direct cathode recovery from unspecified mixed black mass should therefore be treated as high risk unless it demonstrates a validated conversion route rather than simple relithiation.

### 3.2 Mechanical pretreatment

Mechanical pretreatment can include discharge, dismantling, crushing or shredding, sieving and separation of metals, plastics and active-material fractions. Its central output is often black mass containing cathode active material, graphite and residual contaminants.

Pretreatment serves four functions:

1. remove pack and cell hardware that does not belong in the chemical process;
2. liberate electrode coatings from aluminium and copper current collectors;
3. enrich active materials into black mass;
4. reduce downstream reagent and impurity burdens.

It can also be a major loss point. Cathode particles can remain attached to foils, enter coarse fractions, become entrained with graphite or be lost as dust. JRC assessments specifically note losses of active electrode materials during mechanical separation [[1]](https://publications.jrc.ec.europa.eu/repository/handle/JRC129861).

An LFP mass-balance study reports recovery of up to 97% of plastics and 85.3% of graphite during physical processing, illustrating that non-cathode recovery can materially affect whole-battery efficiency [[20]](https://pubmed.ncbi.nlm.nih.gov/41552450/). These percentages are fraction-specific results, not universal whole-cell coefficients.

Thermal pretreatment may remove binder and electrolyte residues and improve separation. It is not synonymous with pyrometallurgical metal recovery: a low-temperature binder-removal step followed by leaching is still primarily a mechanical-hydrometallurgical route.

### 3.3 Pyrometallurgy

Pyrometallurgy uses high-temperature treatment to destroy organic components and separate metals among alloy, slag, dust and gas streams.

Its advantages are:

- tolerance of heterogeneous input;
- established high-throughput processing;
- reduced need for exact cathode sorting;
- concentration of nickel and cobalt into a metal-bearing phase for subsequent refining.

Its principal limitations are:

- high energy demand;
- combustion or decomposition of organic fractions;
- need for off-gas control;
- poor conventional lithium recovery unless slag or dust receives additional treatment;
- tendency for manganese to report partly to slag;
- weak economics for dedicated LFP treatment because LFP lacks intrinsic nickel and cobalt.

JRC evidence states that pyrometallurgical routes generally fail to recover lithium unless the slag is further refined [[1]](https://publications.jrc.ec.europa.eu/repository/handle/JRC129861). Consequently, “recovered into slag” should not be accepted as final lithium recovery unless the slag enters a validated downstream operation and the qualifying output is measured.

For NMC, a pyro-hydrometallurgical combination can use smelting for robust concentration, followed by aqueous refining. In procurement, it should be evaluated as an integrated chain. Quoting only the Ni/Co alloy recovery obscures lithium and manganese fate.

For LFP and LMFP, conventional smelting risks converting iron and phosphorus into low-value slag phases. A specialized thermal route may recover lithium, but the presence of a technical possibility does not establish a general commercial coefficient.

### 3.4 Hydrometallurgy

Hydrometallurgy uses aqueous leaching followed by purification, solvent extraction, ion exchange, crystallization or precipitation.

Its strengths are:

- comparatively high selectivity;
- recovery of lithium as well as transition metals;
- ability to produce high-purity salts or precursors;
- adaptability through pH, redox and reagent control.

Its weaknesses are:

- acid, base and reductant consumption;
- multiple liquid-solid separations;
- saline residues and wastewater;
- sensitivity to aluminium, copper, fluorine, iron and phosphate contamination;
- gap between extraction and final-product yield.

For NMC, acidic reductive leaching transfers lithium, nickel, cobalt and manganese to solution. Purification then removes copper, aluminium and iron before separation or coprecipitation of the target metals [[2]](https://pubs.rsc.org/en/content/articlehtml/2023/su/d3su00142c).

For LFP, two broad hydrometallurgical philosophies exist:

1. **Selective delithiation:** lithium moves into solution while the Fe–P framework remains as FePO₄.
2. **Full dissolution and reprecipitation:** Li, Fe and P enter solution and are subsequently separated or recombined.

Selective delithiation can reduce downstream iron separation, but Fe and P are only recovered if the retained solid becomes a qualifying product.

For LMFP, manganese complicates the LFP pattern because it may need to be retained in a regenerated mixed phosphate or separated from iron. The chemistry-specific study in the evidence uses leaching followed by pH-controlled gradient precipitation of iron, manganese and lithium phosphates [[6]](https://www.sciencedirect.com/science/article/abs/pii/S221499372300060X).

### 3.5 Direct regeneration and upcycling

Direct regeneration attempts to preserve the active-material structure and restore lost lithium, oxidation state and crystal order.

For LFP, degradation can produce lithium vacancies, FePO₄ phases and Li/Fe antisite defects. Relithiation and reduction can restore the LFP structure [[3]](https://www.mdpi.com/2313-0105/11/1/33) [[4]](https://www.oaepublish.com/articles/energymater.2023.57). Direct processing may avoid the long chain of dissolution, separation and precursor resynthesis.

For NMC, direct recycling similarly uses separation, relithiation and thermal treatment. Peer-reviewed work reports major energy savings and strong electrochemical performance, but also identifies chemistry inflexibility and impurity separation as central barriers [[14]](https://www.sciopen.com/local/article_pdf/10.1002/eem2.12863.pdf).

Direct recycling has four qualification conditions:

- chemistry and formulation must be known;
- active material must be adequately separated from graphite and metals;
- ageing-related defects must be repairable;
- the regenerated material must meet product specifications, not merely display acceptable laboratory capacity.

Spent-LFP-to-LMFP upcycling is a distinct pathway. It adds a manganese source and restructures the LFP-family material into LMFP. Reported products achieved about 144.7 mAh/g and 91.1% capacity retention after 500 cycles in the cited experimental work [[8]](https://pubs.rsc.org/en/content/articlehtml/2026/sc/d6sc03686d). This demonstrates product performance, not recovery of manganese from spent LMFP, because manganese was deliberately added.

## 4. Element-level transfer evidence

### 4.1 Interpretation rules

Table 1 records the best quantitative or directional evidence supplied for the intrinsic cathode elements. Entries marked “leaching” are not whole-cell transfer coefficients. Where a solid framework is retained, both the liquid and solid destinations are shown.

### Table 1. Transfer-coefficient evidence by chemistry, element, route and destination

| Chemistry | Element | Route and feed scope | Reported transfer or performance | Destination | Metric class | Evidence interpretation |
|---|---|---|---:|---|---|---|
| LFP | Li | Selective oxidative hydrometallurgy; prepared spent LFP cathode | 98.3% | Leachate | Experimentally measured leaching | Strong evidence for cathode-to-solution transfer under the tested conditions; not a pack-to-product coefficient [[4]](https://www.oaepublish.com/articles/energymater.2023.57). |
| LFP | Li | Ammonium-sulfate/H₂O₂ treatment; cathode material | 97.7% | Leachate | Experimentally measured leaching | Does not include precipitation or product purification [[17]](https://www.sciencedirect.com/science/article/abs/pii/S2352152X24034182). |
| LFP | Fe | Same experiment as preceding row | 1.26% leached | Leachate; balance predominantly solid | Experimentally measured leaching | Low solution transfer is consistent with deliberate Fe retention, not 1.26% total recovery [[17]](https://www.sciencedirect.com/science/article/abs/pii/S2352152X24034182). |
| LFP | P | Same experiment | 16.15% leached | Leachate; majority in solid | Experimentally measured leaching | Phosphorus fate must be assessed across both streams [[17]](https://www.sciencedirect.com/science/article/abs/pii/S2352152X24034182). |
| LFP | Li | Acetic-acid selective process; cathode material | Approximately 96% | Leachate | Experimentally measured extraction | Tested at mild conditions; downstream lithium-product yield not established by this percentage [[5]](https://pubmed.ncbi.nlm.nih.gov/41946108/). |
| LFP | Fe | Same selective process | Less than 0.1% dissolved | Predominantly FePO₄-bearing solid | Experimentally measured dissolution/retention | Potentially useful precursor retention if the solid is qualified [[5]](https://pubmed.ncbi.nlm.nih.gov/41946108/). |
| LFP | P | Same selective process | Approximately 3% dissolved | Predominantly solid | Experimentally measured dissolution/retention | Demonstrates selectivity, not final phosphorus recovery [[5]](https://pubmed.ncbi.nlm.nih.gov/41946108/). |
| LFP | Li | Hydro route with precipitation | Lithium carbonate reported up to 99.51% purity | Li₂CO₃ product | Product purity | Purity does not reveal the percentage of feed lithium captured in the product [[18]](https://pmc.ncbi.nlm.nih.gov/articles/PMC10180280/). |
| LFP | Fe, P | Hydro route and precursor reuse | Recovered FePO₄ reused to synthesize LFP; reported regenerated performance up to 158 mAh/g | FePO₄ precursor/new LFP | Product qualification evidence | Supports functional reuse, but the supplied summary does not state a complete Fe or P yield [[18]](https://pmc.ncbi.nlm.nih.gov/articles/PMC10180280/). |
| LFP | Li, Fe, P | Direct regeneration | No complete elemental coefficient reported | Regenerated LFP | Functional-material route | Elements are preserved in the cathode framework, but recovered lithium must exclude externally added relithiation material [[3]](https://www.mdpi.com/2313-0105/11/1/33) [[4]](https://www.oaepublish.com/articles/energymater.2023.57). |
| LFP | Ni, Co | Any route | N/A | N/A | Chemistry definition | Ni and Co are not intrinsic LFP cathode constituents. |
| LMFP | Li, Mn, Fe, P | Sulfuric-acid/oxidant leaching of spent LMFP cathode | Approaching 100% under optimized conditions | Pregnant leach solution | Experimentally measured leaching | Single chemistry-specific study group; insufficient to establish industrial or whole-cell transfer [[6]](https://www.sciencedirect.com/science/article/abs/pii/S221499372300060X). |
| LMFP | Fe | Gradient precipitation after LMFP leaching | Sequential recovery proposed as FePO₄·2H₂O | Solid phosphate | Thermodynamic/experimental process evidence | Final mass yield is not specified in the supplied evidence [[6]](https://www.sciencedirect.com/science/article/abs/pii/S221499372300060X). |
| LMFP | Mn | Gradient precipitation after LMFP leaching | Sequential recovery proposed as Mn₃(PO₄)₂·3H₂O | Solid phosphate | Thermodynamic/experimental process evidence | Chemistry-specific but narrow evidence base [[6]](https://www.sciencedirect.com/science/article/abs/pii/S221499372300060X). |
| LMFP | Li | Gradient precipitation after LMFP leaching | Sequential recovery proposed as Li₃PO₄ | Solid lithium phosphate | Thermodynamic/experimental process evidence | Leaching near 100% does not establish near-100% lithium-product yield [[6]](https://www.sciencedirect.com/science/article/abs/pii/S221499372300060X). |
| LMFP | Li, Fe, P | LFP-to-LMFP direct upcycling | Product capacity about 144.7 mAh/g; 91.1% retention after 500 cycles | Upcycled LMFP | Product-performance evidence | Demonstrates use of spent LFP as feed, not recovery from end-of-life LMFP [[7]](https://pmc.ncbi.nlm.nih.gov/articles/PMC13224291/) [[8]](https://pubs.rsc.org/en/content/articlehtml/2026/sc/d6sc03686d). |
| LMFP | Mn | LFP-to-LMFP direct upcycling | Manganese introduced from an external source | Upcycled LMFP | Added input, not recovered element | Must not be counted as recovered Mn from the waste feed [[7]](https://pmc.ncbi.nlm.nih.gov/articles/PMC13224291/) [[8]](https://pubs.rsc.org/en/content/articlehtml/2026/sc/d6sc03686d). |
| LMFP | Ni, Co | Any route | N/A | N/A | Chemistry definition | Ni and Co are not intrinsic LMFP cathode constituents. |
| NMC | Li, Ni, Co, Mn | Optimized hydrometallurgical routes | Often greater than 95%; some reviews report above 99% under optimized conditions | Leachate and subsequently recovered salts/precursors | Primarily leaching/reviewed process performance | Broadly supports high technical potential, but route and product basis vary [[2]](https://pubs.rsc.org/en/content/articlehtml/2023/su/d3su00142c). |
| NMC with LFP co-feed | Li, Co | Sulfuric-acid synergistic leaching | Approximately 100% in cited experiments | Pregnant leach solution | Experimentally measured leaching | LFP supplies reductive Fe²⁺; values remain feed- and condition-specific [[15]](https://www.nature.com/articles/s41598-024-61569-3). |
| NMC with LFP co-feed | Ni | Same mixed-feed process | Approximately 87.6% | Pregnant leach solution | Experimentally measured leaching | Lower than generalized >95% claims; illustrates process-condition sensitivity [[15]](https://www.nature.com/articles/s41598-024-61569-3). |
| NMC with LFP co-feed | Mn | Same mixed-feed process | Approximately 91.1% | Pregnant leach solution | Experimentally measured leaching | Does not include final manganese separation [[15]](https://www.nature.com/articles/s41598-024-61569-3). |
| NMC with LFP co-feed | Fe | Purification by pH adjustment | 97.8% removed from solution | Predominantly iron-phosphate precipitate | Impurity-removal efficiency | This is removal from NMC product liquor, not necessarily functional Fe recovery [[16]](https://www.sciencedirect.com/science/article/pii/S0892687524004667). |
| NMC | Li, Ni, Mn, Co | One hydrometallurgical mass-balance example | Leaching: 83%, 71.15%, 85.82%, 99.76%, respectively | Leachate; final product 43.5 kg from 100 kg cathode waste | Experiment and process mass balance | Demonstrates that practical results can be substantially below optimized review values [[21]](https://pdfs.semanticscholar.org/c661/a55033618d5da0fccea635908bea89585d7f.pdf). |
| NMC | Li, Ni, Co, Mn | Direct regeneration | No universal elemental coefficient reported | Regenerated NMC cathode | Functional-material route | High retention is conceptually possible, but purity and chemistry matching constrain scalability [[14]](https://www.sciopen.com/local/article_pdf/10.1002/eem2.12863.pdf). |
| NMC | Fe, P | NMC-only route | N/A | N/A | Chemistry definition | Fe and P are not intrinsic NMC cathode elements; if present they are impurities or mixed-feed constituents. |

**Scope and units:** percentages are mass percentages of the named element transferred or leached from the specific experimental feed unless otherwise stated. Product purity and electrochemical performance use their stated units. Dates vary by study and do not represent a common reference year.

**Evidence limitation:** Three independent, high-quality chemistry-specific source groups are not available for most individual LMFP coefficients, direct-recycling yields or complete LFP Fe/P product balances. The table therefore reports the evidence as found and does not manufacture a consensus coefficient.

### 4.2 LFP element fate

#### Lithium

Lithium is generally the principal soluble target in selective LFP hydrometallurgy. Several independent peer-reviewed source groups report cathode-scale extraction in the mid-to-high 90% range [[4]](https://www.oaepublish.com/articles/energymater.2023.57) [[17]](https://www.sciencedirect.com/science/article/abs/pii/S2352152X24034182) [[5]](https://pubmed.ncbi.nlm.nih.gov/41946108/). This supports a high maximum technical scenario, but not an assumption that every industrial process will deliver more than 95% saleable lithium.

Lithium losses may occur in:

- black-mass tailings;
- FePO₄ residue;
- purification sludge;
- mother liquor;
- off-spec lithium product; or
- thermal slag.

#### Iron and phosphorus

Iron and phosphorus should normally be evaluated together because selective delithiation can retain them as FePO₄. A low Fe or P leaching value can be positive if the solid is purified and reused. It is negative if the same solid is discarded, used only in a low-substitution application or counted without evidence of destination.

A recycler should therefore report:

- Fe and P input in black mass;
- Fe and P transferred to leachate;
- Fe and P retained in residue;
- purity and moisture of the FePO₄ product;
- actual product acceptance or destination;
- losses to wastewater and disposal.

### 4.3 LMFP element fate

LMFP introduces intrinsic manganese into the phosphate framework. Its recovery options include:

- retaining Mn and Fe together in directly regenerated LMFP;
- dissolving all intrinsic elements and sequentially precipitating iron, manganese and lithium phosphates;
- converting the solution to a new mixed precursor;
- separating manganese into a distinct salt.

The narrow evidence base prevents reliable assignment of industrial coefficients. The chemistry-specific study reporting near-complete leaching is useful proof of feasibility but remains a leach-stage result [[6]](https://www.sciencedirect.com/science/article/abs/pii/S221499372300060X).

Moreover, commercial dopants and mixed-feed contaminants can make manganese attribution difficult. A manganese balance must distinguish manganese originating in LMFP from manganese in NMC or other manganese-containing cathodes.

### 4.4 NMC element fate

#### Nickel and cobalt

Nickel and cobalt have strong economic and technical recovery incentives. Both can be concentrated into an alloy in pyrometallurgy or transferred into solution in hydrometallurgy. EU material-recovery requirements of 90% by the end of 2027 and 95% by the end of 2031 create a clear compliance floor [[9]](https://environment.ec.europa.eu/news/new-rules-boost-recycling-efficiency-waste-batteries-2025-07-04_en) [[11]](https://eur-lex.europa.eu/legal-content/uk/LSU/?uri=CELEX%3A32023R1542).

#### Lithium

Lithium is the clearest discriminator between conventional smelting and integrated recovery. In a pyro-only route it commonly reports to slag; a qualifying system therefore needs slag leaching, volatilization or another downstream recovery stage [[1]](https://publications.jrc.ec.europa.eu/repository/handle/JRC129861).

#### Manganese

Manganese is intrinsic to NMC but is not covered by the cited EU element-specific recovery targets. It may enter solution in hydrometallurgy, remain partly in slag after smelting or be preserved in direct regeneration. Contracts should establish a manganese recovery requirement rather than infer it from nickel and cobalt performance.

#### Iron and phosphorus

For an NMC-only cathode, Fe and P are N/A. In mixed NMC/LFP processing, however, Fe²⁺ from LFP can act as an internal reductant and phosphate can assist iron removal [[15]](https://www.nature.com/articles/s41598-024-61569-3) [[16]](https://www.sciencedirect.com/science/article/pii/S0892687524004667). This synergy can reduce external reductant demand, but it also transforms Fe and P into purification constituents whose final destination must be documented.

## 5. Element-recovery scenarios

### Table 2. Minimum/mode/maximum elemental recovery scenarios, 2030, 2050 and 2060

**Metric:** percentage by mass of each intrinsic cathode element entering the main recycling operation that reaches a qualifying recovered product or regenerated cathode output. Collection is excluded. “N/A” means the element is not intrinsic to the named cathode chemistry.

| Chemistry | Element | 2030 min / mode / max (%) | 2050 min / mode / max (%) | 2060 min / mode / max (%) | Scenario basis |
|---|---|---:|---:|---:|---|
| LFP | Li | 70 / 85 / 97 | 80 / 94 / 99 | 85 / 96 / 99 | Upper range anchored by several selective-leaching experiments; mode discounted for pretreatment, purification and product losses [[4]](https://www.oaepublish.com/articles/energymater.2023.57) [[17]](https://www.sciencedirect.com/science/article/abs/pii/S2352152X24034182) [[5]](https://pubmed.ncbi.nlm.nih.gov/41946108/). |
| LFP | Fe | 60 / 85 / 98 | 75 / 92 / 99 | 80 / 94 / 99 | Assumes growing qualification of retained or reprecipitated FePO₄. Complete product-yield evidence is weaker than Li-leaching evidence [[4]](https://www.oaepublish.com/articles/energymater.2023.57) [[5]](https://pubmed.ncbi.nlm.nih.gov/41946108/) [[18]](https://pmc.ncbi.nlm.nih.gov/articles/PMC10180280/). |
| LFP | P | 55 / 80 / 97 | 70 / 90 / 99 | 78 / 93 / 99 | Similar to Fe but with wider near-term losses because P may partition between solution and residue [[17]](https://www.sciencedirect.com/science/article/abs/pii/S2352152X24034182) [[5]](https://pubmed.ncbi.nlm.nih.gov/41946108/) [[18]](https://pmc.ncbi.nlm.nih.gov/articles/PMC10180280/). |
| LFP | Mn | N/A | N/A | N/A | Not intrinsic to LFP. |
| LFP | Ni | N/A | N/A | N/A | Not intrinsic to LFP. |
| LFP | Co | N/A | N/A | N/A | Not intrinsic to LFP. |
| LMFP | Li | 65 / 82 / 96 | 78 / 92 / 98 | 83 / 95 / 99 | Chemistry-specific leaching evidence is narrow; scenario also uses LFP-family analogues [[4]](https://www.oaepublish.com/articles/energymater.2023.57) [[5]](https://pubmed.ncbi.nlm.nih.gov/41946108/) [[6]](https://www.sciencedirect.com/science/article/abs/pii/S221499372300060X). |
| LMFP | Mn | 60 / 80 / 95 | 75 / 90 / 98 | 80 / 93 / 99 | Based mainly on one chemistry-specific leach/gradient-precipitation study plus maturity assumptions [[6]](https://www.sciencedirect.com/science/article/abs/pii/S221499372300060X). Three independent LMFP EOL source groups are unavailable. |
| LMFP | Fe | 55 / 78 / 95 | 70 / 88 / 98 | 78 / 91 / 99 | LFP-family FePO₄ evidence adjusted downward for Mn/Fe separation complexity [[5]](https://pubmed.ncbi.nlm.nih.gov/41946108/) [[18]](https://pmc.ncbi.nlm.nih.gov/articles/PMC10180280/) [[6]](https://www.sciencedirect.com/science/article/abs/pii/S221499372300060X). |
| LMFP | P | 50 / 75 / 94 | 68 / 86 / 98 | 75 / 90 / 99 | Phosphate can be distributed among several precipitates; direct industrial evidence is sparse [[5]](https://pubmed.ncbi.nlm.nih.gov/41946108/) [[18]](https://pmc.ncbi.nlm.nih.gov/articles/PMC10180280/) [[6]](https://www.sciencedirect.com/science/article/abs/pii/S221499372300060X). |
| LMFP | Ni | N/A | N/A | N/A | Not intrinsic to LMFP. |
| LMFP | Co | N/A | N/A | N/A | Not intrinsic to LMFP. |
| NMC | Li | 70 / 85 / 97 | 82 / 94 / 99 | 88 / 97 / 99 | Reflects high hydro potential, poorer conventional pyro fate and the 80% end-2031 legal target [[9]](https://environment.ec.europa.eu/news/new-rules-boost-recycling-efficiency-waste-batteries-2025-07-04_en) [[1]](https://publications.jrc.ec.europa.eu/repository/handle/JRC129861) [[2]](https://pubs.rsc.org/en/content/articlehtml/2023/su/d3su00142c). |
| NMC | Ni | 90 / 95 / 99 | 95 / 98 / 99 | 96 / 99 / 99 | Anchored by legal targets and mature hydro/combined recovery; lower experimental results remain possible [[9]](https://environment.ec.europa.eu/news/new-rules-boost-recycling-efficiency-waste-batteries-2025-07-04_en) [[2]](https://pubs.rsc.org/en/content/articlehtml/2023/su/d3su00142c) [[21]](https://pdfs.semanticscholar.org/c661/a55033618d5da0fccea635908bea89585d7f.pdf). |
| NMC | Co | 90 / 95 / 99 | 95 / 98 / 99 | 96 / 99 / 99 | Same basis as Ni; optimized and lower-performing studies coexist [[15]](https://www.nature.com/articles/s41598-024-61569-3) [[2]](https://pubs.rsc.org/en/content/articlehtml/2023/su/d3su00142c) [[21]](https://pdfs.semanticscholar.org/c661/a55033618d5da0fccea635908bea89585d7f.pdf). |
| NMC | Mn | 75 / 90 / 99 | 88 / 96 / 99 | 92 / 98 / 99 | No cited EU element target; scenario reflects hydrometallurgical potential and possible slag or separation losses [[15]](https://www.nature.com/articles/s41598-024-61569-3) [[2]](https://pubs.rsc.org/en/content/articlehtml/2023/su/d3su00142c) [[21]](https://pdfs.semanticscholar.org/c661/a55033618d5da0fccea635908bea89585d7f.pdf). |
| NMC | Fe | N/A | N/A | N/A | Not intrinsic to NMC cathode. |
| NMC | P | N/A | N/A | N/A | Not intrinsic to NMC cathode. |

**Scenario status:** all numerical ranges in Table 2 are analyst scenarios. They are not legal targets, published plant guarantees or forecasts reported by the cited sources.

**Why the 2030 minimum for NMC Ni and Co is 90%:** the EU requires 90% material recovery by the end of 2027. The 95% requirement begins at the end of 2031, so 95% is used as the 2030 mode rather than represented as a 2030 legal minimum [[9]](https://environment.ec.europa.eu/news/new-rules-boost-recycling-efficiency-waste-batteries-2025-07-04_en) [[11]](https://eur-lex.europa.eu/legal-content/uk/LSU/?uri=CELEX%3A32023R1542).

**Why 2050 and 2060 do not approach 100% in every case:** sorting losses, contamination, thermodynamic partitioning, quality rejection and practical residue management remain. The values are rounded planning assumptions, not claims of numerical forecasting precision.

### 5.1 Collection-adjusted interpretation

If a fraction of end-of-life batteries never reaches the recycler, system recovery is lower than Table 2. For example, a process coefficient of 95% combined with an 80% collection rate would yield a collection-adjusted transfer of 76% before other system losses. This arithmetic is illustrative, not a forecast.

The distinction matters because EU portable and light-means-of-transport collection targets do not provide a generic numerical EV-battery collection coefficient. Applying portable-battery collection percentages to BEV traction packs would be inappropriate.

## 6. Overall recycling efficiency versus elemental recovery

EU recycling efficiency concerns the mass of the battery recycled, while material recovery concerns specified elements. A process can attain high whole-battery recycling efficiency by recovering steel, aluminium, copper, plastics or graphite while losing a substantial fraction of lithium. Conversely, a process can recover nearly all cathode lithium from clean black mass but perform poorly at whole-battery level if pretreatment rejects large fractions.

### Table 3. Overall recycling-efficiency scenarios distinct from elemental recovery

**Metric:** qualifying recycled output mass divided by waste-battery input mass at the recycling operation. Percent by mass; collection excluded. These are analyst scenarios, except the separately identified legal floors.

| Chemistry | 2030 min / mode / max (%) | 2050 min / mode / max (%) | 2060 min / mode / max (%) | Main determinants |
|---|---:|---:|---:|---|
| LFP | 70 / 76 / 85 | 73 / 83 / 91 | 75 / 86 / 93 | Recovery of graphite, aluminium, copper, plastics and Fe–P product is essential because cathode metals alone do not dominate whole-cell mass value [[20]](https://pubmed.ncbi.nlm.nih.gov/41552450/) [[13]](https://environment.ec.europa.eu/document/download/6297f987-49f6-432b-8119-d60fb6a26c9b_en?filename=COM_2026_470_1_EN_ACT_part1_v3.pdf) [[1]](https://publications.jrc.ec.europa.eu/repository/handle/JRC129861). |
| LMFP | 70 / 75 / 84 | 73 / 82 / 90 | 75 / 85 / 92 | Same whole-cell challenge as LFP, with additional Mn/Fe separation or direct-regeneration requirements [[13]](https://environment.ec.europa.eu/document/download/6297f987-49f6-432b-8119-d60fb6a26c9b_en?filename=COM_2026_470_1_EN_ACT_part1_v3.pdf) [[1]](https://publications.jrc.ec.europa.eu/repository/handle/JRC129861) [[6]](https://www.sciencedirect.com/science/article/abs/pii/S221499372300060X). |
| NMC | 70 / 78 / 87 | 75 / 84 / 92 | 78 / 87 / 94 | Strong Ni/Co recovery, improving lithium capture and broader non-cathode recovery [[13]](https://environment.ec.europa.eu/document/download/6297f987-49f6-432b-8119-d60fb6a26c9b_en?filename=COM_2026_470_1_EN_ACT_part1_v3.pdf) [[1]](https://publications.jrc.ec.europa.eu/repository/handle/JRC129861) [[2]](https://pubs.rsc.org/en/content/articlehtml/2023/su/d3su00142c). |
| Mixed lithium-based feed | 70 / 75 / 84 | 72 / 82 / 90 | 75 / 85 / 92 | Feed heterogeneity, active-material losses in pretreatment and purification-residue management [[15]](https://www.nature.com/articles/s41598-024-61569-3) [[13]](https://environment.ec.europa.eu/document/download/6297f987-49f6-432b-8119-d60fb6a26c9b_en?filename=COM_2026_470_1_EN_ACT_part1_v3.pdf) [[1]](https://publications.jrc.ec.europa.eu/repository/handle/JRC129861). |
| Binding EU minimum for lithium-based batteries | **70 by end-2030** | Not specified in supplied evidence | Not specified in supplied evidence | The preceding legal minimum is 65% by end-2025 [[9]](https://environment.ec.europa.eu/news/new-rules-boost-recycling-efficiency-waste-batteries-2025-07-04_en) [[10]](https://eur-lex.europa.eu/EN/legal-content/summary/sustainability-rules-for-batteries-and-waste-batteries.html). |

The higher mode values for 2050 and 2060 assume recovery of fractions that are currently lost or excluded, including wider graphite and Fe/P valorization. They do not represent adopted EU targets. The Commission/JRC assessment concludes that the 70% end-2030 target is feasible under the regulatory calculation methodology, including transitional flexibility [[13]](https://environment.ec.europa.eu/document/download/6297f987-49f6-432b-8119-d60fb6a26c9b_en?filename=COM_2026_470_1_EN_ACT_part1_v3.pdf).

## 7. EU legal and policy requirements

### 7.1 Binding recycling and material-recovery targets

Regulation (EU) 2023/1542 governs the battery life cycle and replaced the earlier directive framework. Commission Delegated Regulation (EU) 2025/606 supplies the harmonized methodology for recycling-efficiency and material-recovery calculations [[9]](https://environment.ec.europa.eu/news/new-rules-boost-recycling-efficiency-waste-batteries-2025-07-04_en) [[10]](https://eur-lex.europa.eu/EN/legal-content/summary/sustainability-rules-for-batteries-and-waste-batteries.html) [[12]](https://revivebatts.com/battery-recycling-efficiency-eu-2026/).

### Table 4. Binding EU targets and implementation timeline

| Date | Requirement | Scope and metric | Status as of 15 September 2026 |
|---|---|---|---|
| 31 Dec. 2025 | Recycling efficiency: **65%** | Lithium-based waste batteries; mass of qualifying recycled outputs relative to battery input | Binding target [[9]](https://environment.ec.europa.eu/news/new-rules-boost-recycling-efficiency-waste-batteries-2025-07-04_en) [[10]](https://eur-lex.europa.eu/EN/legal-content/summary/sustainability-rules-for-batteries-and-waste-batteries.html). |
| 31 Dec. 2027 | Material recovery: **50% Li** | Lithium in relevant waste batteries | Binding target [[9]](https://environment.ec.europa.eu/news/new-rules-boost-recycling-efficiency-waste-batteries-2025-07-04_en) [[11]](https://eur-lex.europa.eu/legal-content/uk/LSU/?uri=CELEX%3A32023R1542). |
| 31 Dec. 2027 | Material recovery: **90% Co, Cu, Pb and Ni** | Each named element; not a combined average | Binding target [[9]](https://environment.ec.europa.eu/news/new-rules-boost-recycling-efficiency-waste-batteries-2025-07-04_en) [[11]](https://eur-lex.europa.eu/legal-content/uk/LSU/?uri=CELEX%3A32023R1542). |
| 2027 | Portable-battery collection: **63%** | Portable batteries; collection metric, not an EV-pack recycling coefficient | Binding category target reported by Commission sources [[22]](https://environment.ec.europa.eu/news/new-law-more-sustainable-circular-and-safe-batteries-enters-force-2023-08-17_en). |
| 2028 | LMT-battery collection: **51%** | Light means of transport batteries; not BEV traction batteries | Binding category target reported in the supplied policy evidence [[22]](https://environment.ec.europa.eu/news/new-law-more-sustainable-circular-and-safe-batteries-enters-force-2023-08-17_en). |
| 31 Dec. 2030 | Recycling efficiency: **70%** | Lithium-based waste batteries; whole-battery mass metric | Binding target [[9]](https://environment.ec.europa.eu/news/new-rules-boost-recycling-efficiency-waste-batteries-2025-07-04_en) [[10]](https://eur-lex.europa.eu/EN/legal-content/summary/sustainability-rules-for-batteries-and-waste-batteries.html). |
| 2030 | Portable-battery collection: **73%** | Portable batteries | Binding category target [[22]](https://environment.ec.europa.eu/news/new-law-more-sustainable-circular-and-safe-batteries-enters-force-2023-08-17_en). |
| 31 Dec. 2031 | Material recovery: **80% Li** | Element-specific recovery | Binding target [[9]](https://environment.ec.europa.eu/news/new-rules-boost-recycling-efficiency-waste-batteries-2025-07-04_en) [[11]](https://eur-lex.europa.eu/legal-content/uk/LSU/?uri=CELEX%3A32023R1542). |
| 31 Dec. 2031 | Material recovery: **95% Co, Cu, Pb and Ni** | Each named element | Binding target [[9]](https://environment.ec.europa.eu/news/new-rules-boost-recycling-efficiency-waste-batteries-2025-07-04_en) [[11]](https://eur-lex.europa.eu/legal-content/uk/LSU/?uri=CELEX%3A32023R1542). |
| 2031 | LMT-battery collection: **61%** | Light means of transport batteries | Binding category target reported in supplied policy evidence [[22]](https://environment.ec.europa.eu/news/new-law-more-sustainable-circular-and-safe-batteries-enters-force-2023-08-17_en). |
| 18 Aug. 2031 | Recycled content: **16% Co, 6% Li, 6% Ni** | Active materials in covered industrial, EV and SLI batteries; recovered from manufacturing or post-consumer waste | Binding future product requirement [[10]](https://eur-lex.europa.eu/EN/legal-content/summary/sustainability-rules-for-batteries-and-waste-batteries.html). |
| 18 Aug. 2036 | Recycled content: **26% Co, 12% Li, 15% Ni** | Covered industrial, EV and SLI batteries | Binding future product requirement [[10]](https://eur-lex.europa.eu/EN/legal-content/summary/sustainability-rules-for-batteries-and-waste-batteries.html). |

Lead recycled-content requirements also exist, but lead is outside the chemistry scope of this report.

No corresponding element-specific recovery target for manganese, iron or phosphorus is identified in the supplied legislation. Their recovery can nevertheless affect whole-battery recycling efficiency and commercial circularity.

### 7.2 Regulation (EU) 2025/606: calculation and verification

Delegated Regulation (EU) 2025/606:

- defines harmonized calculations for recycling efficiency and material recovery;
- identifies permissible input and output fractions;
- requires standardized documentation;
- supports traceability of final fractions;
- reduces double-counting risk; and
- applies specifically to recycling efficiency and material recovery, not to the separate recycled-content calculation for new batteries [[9]](https://environment.ec.europa.eu/news/new-rules-boost-recycling-efficiency-waste-batteries-2025-07-04_en) [[12]](https://revivebatts.com/battery-recycling-efficiency-eu-2026/).

The distinction between the two methodologies is important:

- **2025/606** governs waste-battery recycling performance.
- The recycled-content methodology under Article 8 is a separate chain-of-custody and verification matter. JRC work addresses calculation and verification of cobalt, lithium, nickel and lead recovered from manufacturing or post-consumer waste [[23]](https://publications.jrc.ec.europa.eu/repository/handle/JRC146717).

The temporary treatment of graphite, iron and phosphorus through the end of 2029 provides transition flexibility [[13]](https://environment.ec.europa.eu/document/download/6297f987-49f6-432b-8119-d60fb6a26c9b_en?filename=COM_2026_470_1_EN_ACT_part1_v3.pdf). It should not be used as a product strategy. From 2030 onward, an LFP recycler relying on excluded Fe/P fractions faces greater compliance and commercial exposure.

### 7.3 Recycled content

The recycled-content obligations create demand for verified secondary cobalt, lithium and nickel:

- 2031: 16% cobalt, 6% lithium and 6% nickel;
- 2036: 26% cobalt, 12% lithium and 15% nickel [[10]](https://eur-lex.europa.eu/EN/legal-content/summary/sustainability-rules-for-batteries-and-waste-batteries.html).

These requirements are not recovery rates. A recycler achieving 95% nickel recovery does not thereby prove that a new battery contains the required recycled share. The latter needs chain-of-custody records connecting eligible waste origin, recovered material, active-material production and the covered battery.

For LFP and LMFP, the lithium requirement is directly relevant. The cobalt and nickel requirements are N/A to the cathode formulation unless those materials occur elsewhere in the covered battery or as non-intentional material. Recycled iron, phosphorus and manganese do not count toward the named Co/Li/Ni minimums.

### 7.4 Collection and extended producer responsibility

The regulation takes a life-cycle approach covering placing on the market, collection and waste management [[22]](https://environment.ec.europa.eu/news/new-law-more-sustainable-circular-and-safe-batteries-enters-force-2023-08-17_en). Producer responsibility is therefore broader than financing metallurgy: it includes organizing compliant end-of-life handling and ensuring that waste batteries enter authorized collection and treatment channels.

The supplied evidence provides numerical collection targets for portable and LMT batteries, but not a generic numerical collection-rate target for BEV traction batteries. Those category percentages should not be substituted into BEV recovery calculations.

A BEV operator should nevertheless contractually track:

- batteries reaching retirement;
- batteries routed to second use;
- batteries exported or transferred;
- batteries delivered to authorized recyclers;
- mass and chemistry reconciliation;
- final treatment and material destinations.

### 7.5 Due diligence

The Batteries Regulation requires relevant economic operators to establish battery due-diligence policies addressing social and environmental risks associated with sourcing, processing and trading covered raw and secondary materials. The supplied Commission evidence identifies lithium, cobalt, nickel and natural graphite among the relevant materials [[22]](https://environment.ec.europa.eu/news/new-law-more-sustainable-circular-and-safe-batteries-enters-force-2023-08-17_en).

Required functions include management systems, risk identification, mitigation and independent verification. Because due-diligence implementation has been amended and clarified through later legislation, operators should use current consolidated legal text rather than relying only on the original 2023 timetable [[10]](https://eur-lex.europa.eu/EN/legal-content/summary/sustainability-rules-for-batteries-and-waste-batteries.html).

For recycled material, due diligence should cover more than mine origin. Relevant risks include:

- undocumented cross-border waste movement;
- unsafe dismantling;
- hazardous releases;
- misclassification of black mass;
- false recycled-content attribution;
- blending that obscures origin.

### 7.6 Passport and traceability

The regulation establishes a digital battery passport for EV, LMT and specified industrial batteries. It is intended to carry information supporting identification, composition, sustainability and circularity. The supplied evidence establishes the passport requirement and its relationship to documentation and traceability, but does not provide a complete article-by-article implementation schedule from primary legislation for every data field [[10]](https://eur-lex.europa.eu/EN/legal-content/summary/sustainability-rules-for-batteries-and-waste-batteries.html).

For recycling decisions, the passport is potentially valuable for:

- chemistry identification;
- manufacturer and model identification;
- dismantling information;
- recycled-content documentation;
- routing and status records.

A passport does not itself prove recovery. It must be reconciled with weighed plant inputs, process records and final-product documentation.

### 7.7 Carbon-footprint requirements

The Batteries Regulation includes carbon-footprint requirements as part of its sustainability framework [[22]](https://environment.ec.europa.eu/news/new-law-more-sustainable-circular-and-safe-batteries-enters-force-2023-08-17_en). JRC work develops calculation methods and default recycling models to support consistent battery carbon-footprint declarations [[24]](https://publications.jrc.ec.europa.eu/repository/handle/JRC141200).

Two points are decision-relevant:

1. recycled content and low carbon footprint are not synonymous;
2. process choice can matter more than the nominal recycled share.

The supplied JRC evidence reports that 30% secondary material produced only a small carbon-footprint change in one assessment, while advanced recycling processes could reduce battery carbon footprint by up to 16% relative to default processes [[24]](https://publications.jrc.ec.europa.eu/repository/handle/JRC141200). These results are model-dependent and should not be generalized to every chemistry or location.

### 7.8 Black mass and waste shipments

The Commission updated the European List of Waste in 2025 to create battery-related waste entries and classify black mass as hazardous waste. The supplied Commission evidence states that this classification, together with waste-shipment controls, restricts export to non-OECD destinations [[25]](https://environment.ec.europa.eu/news/battery-related-waste-codes-update-set-boost-circular-economy-2025-03-05_en).

Operational implications include:

- black mass should not be treated as an ordinary commodity without checking waste status;
- cross-border transfer requires appropriate classification and documentation;
- the final refinery destination matters for both compliance and circularity;
- producing black mass is an intermediate step, not proof of final recycling.

## 8. Uncertainty and sensitivity

### 8.1 Evidence uncertainty

#### LFP

LFP selective-leaching evidence is relatively strong at laboratory cathode scale, with several independent studies reporting lithium extraction around 96–98% [[4]](https://www.oaepublish.com/articles/energymater.2023.57) [[17]](https://www.sciencedirect.com/science/article/abs/pii/S2352152X24034182) [[5]](https://pubmed.ncbi.nlm.nih.gov/41946108/). The weaker link is complete whole-cell product yield for Fe and P. Many studies demonstrate retention or precursor reuse but do not provide a harmonized pack-to-product mass balance.

#### LMFP

LMFP is the weakest-evidence chemistry in this report. Direct end-of-life LMFP studies are sparse, and the principal quantitative chemistry-specific evidence comes from a limited study group [[6]](https://www.sciencedirect.com/science/article/abs/pii/S221499372300060X). LFP-to-LMFP upcycling evidence is relevant to technology options but not to spent-LMFP recovery coefficients [[7]](https://pmc.ncbi.nlm.nih.gov/articles/PMC13224291/) [[8]](https://pubs.rsc.org/en/content/articlehtml/2026/sc/d6sc03686d).

#### NMC

NMC has the broadest evidence base, but reported outcomes vary. Reviews describe optimized recovery above 95%, while a specific mass-balance study reports 71.15% nickel, 83% lithium, 85.82% manganese and 99.76% cobalt leaching [[2]](https://pubs.rsc.org/en/content/articlehtml/2023/su/d3su00142c) [[21]](https://pdfs.semanticscholar.org/c661/a55033618d5da0fccea635908bea89585d7f.pdf). The discrepancy is not necessarily a contradiction: feed, process conditions, metric definitions and downstream boundaries differ.

### 8.2 Main sensitivity variables

| Variable | LFP sensitivity | LMFP sensitivity | NMC sensitivity |
|---|---|---|---|
| Collection | High for system recovery | High | High |
| Chemistry sorting | High for direct regeneration | Very high | High |
| Black-mass liberation | High | High | High |
| Aluminium/copper contamination | High for FePO₄ quality | High for phosphate separation | High for solution purification |
| Graphite separation | Affects whole-battery efficiency and product purity | Same | Same |
| Redox control | Governs selective Li release and Fe retention | Governs Fe/Mn behavior | Governs Co/Mn dissolution |
| pH control | Fe/P partition and lithium precipitation | Fe/Mn/Li phosphate separation | Fe/Al removal and Ni/Co/Mn losses |
| Thermal-route slag treatment | Critical for Li | Critical for Li and Mn | Critical for Li and Mn |
| Product specification | Critical for direct and FePO₄ routes | Critical for direct LMFP | Critical for direct NMC and precursor products |
| Feed mixing | Can supply reductant value but contaminate products | Attribution and separation risk | Can benefit leaching but raises Fe/P purification burden |

### 8.3 Sensitivity of system recovery to collection

Collection is multiplicative. Even excellent process performance cannot compensate for missing feed. If collection is 70% and process recovery is 95%, at most 66.5% of the arising element reaches the recovered output before any additional system losses. If collection improves to 90%, the corresponding value is 85.5%.

This is why process procurement and producer-responsibility performance must be audited separately.

### 8.4 Sensitivity to destination rules

Element transfer changes depending on what counts as recovery:

- FePO₄ reused as a cathode precursor: potentially high-quality recovery.
- Fe/P residue used in an application with uncertain substitution: lower-confidence recovery.
- Lithium-bearing slag stored for possible future treatment: inventory, not final recovery.
- Mixed Ni/Co alloy sent to a refinery: intermediate transfer, requiring downstream reconciliation.
- Regenerated cathode failing cell qualification: not an acceptable high-value product, even if elemental retention is high.

### 8.5 Scenario uncertainty ranges

The minimum/mode/maximum ranges should not be interpreted statistically. They are structured planning cases.

Uncertainty is lowest for:

- EU statutory targets;
- the qualitative weakness of conventional pyro lithium recovery;
- laboratory feasibility of high LFP lithium extraction;
- high hydrometallurgical recovery potential for NMC.

Uncertainty is highest for:

- commercial direct-regeneration yields;
- LMFP element-by-element industrial performance;
- Fe and P qualification rates;
- whole-battery efficiencies after 2030;
- all chemistry-specific 2060 values.

## 9. Recommendations

### 9.1 Adopt chemistry-specific routing

Establish at least three routing classes:

1. **Clean LFP stream:** selective hydrometallurgy or qualified direct regeneration.
2. **Clean LMFP stream:** dedicated pilot qualification, with explicit Mn/Fe/P balance.
3. **NMC stream:** hydrometallurgy or integrated pyro-hydrometallurgy with verified lithium recovery.

Mixed streams should be accepted only where the recycler demonstrates that LFP’s reductive and phosphate behavior is intentionally integrated into the flowsheet [[15]](https://www.nature.com/articles/s41598-024-61569-3) [[16]](https://www.sciencedirect.com/science/article/pii/S0892687524004667).

### 9.2 Contract on transfer to products, not extraction alone

For each intrinsic element, require:

- input mass and assay;
- pretreatment distribution;
- leachate and residue distribution;
- isolated product mass, grade and moisture;
- recycled process-stream accounting;
- disposal and wastewater losses;
- final buyer or internal reuse destination;
- recovery calculated under Regulation (EU) 2025/606 where applicable.

A contract stating “greater than 95% leaching” is insufficient.

### 9.3 Set voluntary requirements for untargeted elements

EU law provides specific recovery targets for lithium, nickel and cobalt but not for manganese, iron or phosphorus. A circularity-oriented buyer should establish its own requirements for:

- Mn from LMFP and NMC;
- Fe and P from LFP and LMFP;
- graphite where technically feasible;
- aluminium and copper from pretreatment.

Suggested 2030 contract benchmarks, subject to plant qualification, are the mode values in Table 2 rather than its maxima.

### 9.4 Treat direct recycling as a qualified product process

Direct recycling contracts should specify:

- allowed chemistry and formulation range;
- maximum cross-chemistry contamination;
- external lithium and manganese additions;
- recovered-cathode mass yield;
- elemental origin accounting;
- electrochemical acceptance criteria;
- off-spec reprocessing route.

External relithiation material is not recovered lithium. Manganese added while converting LFP to LMFP is not recovered manganese.

### 9.5 Require a special LMFP qualification campaign

Before awarding long-term LMFP volumes:

1. obtain representative aged LMFP cells;
2. characterize Mn/Fe ratio and dopants;
3. run mechanical and metallurgical mass balances;
4. quantify each intrinsic element across every output;
5. test recovered phosphate or regenerated cathode;
6. repeat with mixed and contaminated feed;
7. establish confidence intervals across batches.

No decision-grade universal LMFP coefficient is presently supported by the supplied evidence.

### 9.6 Separate compliance assurance from circularity performance

The recycler should report three dashboards:

- **Legal:** recycling efficiency and regulated material recovery under EU methodology.
- **Technical:** element transfer by destination.
- **Circularity:** substitution-quality product yield, including non-regulated Fe, P, Mn and graphite.

This prevents a 70% whole-battery result from masking lithium losses and prevents a 98% cathode leach result from being presented as whole-battery recycling.

### 9.7 Build traceability before 2031 recycled-content obligations

Create chain-of-custody records linking:

- battery identity;
- waste origin;
- chemistry and mass;
- pretreatment facility;
- black-mass shipment;
- refining batch;
- recovered product;
- active-material production;
- new battery model.

This structure aligns with the JRC’s emphasis on chain-of-custody and verification for cobalt, lithium and nickel recycled content [[23]](https://publications.jrc.ec.europa.eu/repository/handle/JRC146717).

### 9.8 Plan for 2030 calculation changes

LFP and LMFP recyclers should not base long-term compliance on temporary treatment of iron, phosphorus or graphite. Investment decisions should prioritize:

- graphite separation;
- battery-grade FePO₄ or qualified alternative Fe/P products;
- phosphorus mass-balance closure;
- treatment of lithium-bearing residues;
- harmonized documentation under Regulation 2025/606 [[13]](https://environment.ec.europa.eu/document/download/6297f987-49f6-432b-8119-d60fb6a26c9b_en?filename=COM_2026_470_1_EN_ACT_part1_v3.pdf) [[12]](https://revivebatts.com/battery-recycling-efficiency-eu-2026/).

### 9.9 Use scenario gates rather than a single 2060 forecast

Update the long-term cases at defined gates:

- **2027:** compare actual Li/Ni/Co recovery against EU targets.
- **2030:** verify whole-battery 70% efficiency and treatment of formerly flexible fractions.
- **2031:** verify 80% Li and 95% Ni/Co recovery.
- **2036:** assess demand created by higher recycled-content requirements.
- **Thereafter:** revise 2050 and 2060 assumptions using audited plant data.

## 10. Source quality assessment

### Table 5. Quality assessment for every cited source

| Citation | Source type and authority | Relevance | Limitations or potential bias | Rating |
|---|---|---|---|---|
| [[3]](https://www.mdpi.com/2313-0105/11/1/33) | Peer-reviewed review hosted by MDPI | Broad LFP recycling routes, economics and direct regeneration | Review-level synthesis; individual performance figures may use differing boundaries | Medium–high |
| [[20]](https://pubmed.ncbi.nlm.nih.gov/41552450/) | Peer-reviewed article indexed by PubMed | LFP pretreatment, fraction recovery and mass-balance context | Process-specific; plastics and graphite recovery cannot be generalized to all plants | High |
| [[4]](https://www.oaepublish.com/articles/energymater.2023.57) | Peer-reviewed technical review/article | Selective LFP leaching, FePO₄ retention and direct-regeneration mechanisms | Primarily laboratory evidence; whole-cell downstream yield is incomplete | High |
| [[17]](https://www.sciencedirect.com/science/article/abs/pii/S2352152X24034182) | Peer-reviewed journal article | Quantitative LFP Li, Fe and P leaching values | Single reagent system and optimized conditions; not whole-cell recovery | High |
| [[15]](https://www.nature.com/articles/s41598-024-61569-3) | Peer-reviewed Nature-family article | Mixed LFP/NMC reductive leaching and quantitative metal extraction | Mixed-feed process; coefficients do not apply directly to segregated LFP or NMC plants | High |
| [[13]](https://environment.ec.europa.eu/document/download/6297f987-49f6-432b-8119-d60fb6a26c9b_en?filename=COM_2026_470_1_EN_ACT_part1_v3.pdf) | European Commission technical assessment | Feasibility of EU targets and transitional calculation flexibility | Policy and modeling focus rather than an operating-plant dataset | Very high |
| [[9]](https://environment.ec.europa.eu/news/new-rules-boost-recycling-efficiency-waste-batteries-2025-07-04_en) | European Commission official source | Exact targets and Regulation 2025/606 implementation | Summarizes legal rules; consolidated legal text remains controlling | Very high |
| [[1]](https://publications.jrc.ec.europa.eu/repository/handle/JRC129861) | JRC publication | EU recycling technology, black mass, mechanical losses and pyro lithium limitations | Broad sector assessment; not chemistry-specific plant certification | Very high |
| [[24]](https://publications.jrc.ec.europa.eu/repository/handle/JRC141200) | JRC publication | Carbon-footprint effects of recycling process and secondary material | Model-dependent and sensitive to assumptions; not a universal plant factor | Very high |
| [[5]](https://pubmed.ncbi.nlm.nih.gov/41946108/) | Peer-reviewed indexed article | Quantitative selective LFP Li extraction and Fe/P dissolution | Laboratory conditions and prepared feed; no complete pack-to-product coefficient | High |
| [[16]](https://www.sciencedirect.com/science/article/pii/S0892687524004667) | Peer-reviewed journal article | Quantitative Fe removal and impurity precipitation in mixed processing | Removal from solution is not necessarily functional recovery | High |
| [[18]](https://pmc.ncbi.nlm.nih.gov/articles/PMC10180280/) | Peer-reviewed open-access article | LFP lithium-product purity, FePO₄ recovery and resynthesis performance | Product purity and electrochemical performance do not provide a universal recovery yield | High |
| [[6]](https://www.sciencedirect.com/science/article/abs/pii/S221499372300060X) | Peer-reviewed journal article | Directly relevant spent-LMFP leaching and gradient precipitation | Narrow chemistry-specific evidence base; insufficient replication for an industrial coefficient | High for feasibility; medium for generalization |
| [[7]](https://pmc.ncbi.nlm.nih.gov/articles/PMC13224291/) | Peer-reviewed open-access article | Spent-LFP-to-LMFP upcycling | Studies LFP feed upgraded with added Mn, not end-of-life LMFP recovery | High within its scope |
| [[8]](https://pubs.rsc.org/en/content/articlehtml/2026/sc/d6sc03686d) | Peer-reviewed RSC article | Quantitative electrochemical performance of upcycled LMFP | Product performance rather than element-recovery mass balance | High within its scope |
| [[26]](https://www.sciencedirect.com/science/article/pii/S1383586625044442) | Peer-reviewed review | Comparative environmental and energy ranges for direct recycling | Wide ranges combine dissimilar studies and system boundaries | Medium–high |
| [[2]](https://pubs.rsc.org/en/content/articlehtml/2023/su/d3su00142c) | Peer-reviewed RSC review/article | NMC pyro, hydro and direct routes; recovery potential | Review-level “greater than 99%” results may reflect optimized experiments, not commercial yields | High |
| [[14]](https://www.sciopen.com/local/article_pdf/10.1002/eem2.12863.pdf) | Peer-reviewed technical article | NMC direct-regeneration process, energy and performance | Emerging route; industrial scale and impurity tolerance remain uncertain | High for experiment; medium for deployment |
| [[21]](https://pdfs.semanticscholar.org/c661/a55033618d5da0fccea635908bea89585d7f.pdf) | Technical paper/repository copy of research | Explicit NMC leaching and product mass balance | Accessibility route is less authoritative than the publisher record; process-specific | Medium |
| [[12]](https://revivebatts.com/battery-recycling-efficiency-eu-2026/) | Contextual technical summary of EU 2025/606 | Calculation, documentation and traceability details | Not the legal text itself; used alongside official Commission and EUR-Lex evidence | Medium |
| [[10]](https://eur-lex.europa.eu/EN/legal-content/summary/sustainability-rules-for-batteries-and-waste-batteries.html) | EUR-Lex legal source | Regulation (EU) 2023/1542, amendments and binding obligations | Legal text is authoritative but can be difficult to interpret without consolidated version | Very high |
| [[11]](https://eur-lex.europa.eu/legal-content/uk/LSU/?uri=CELEX%3A32023R1542) | EUR-Lex legal source | Exact end-2027 and end-2031 material-recovery targets | Extracted provision may omit surrounding definitions; read with full regulation | Very high |
| [[23]](https://publications.jrc.ec.europa.eu/repository/handle/JRC146717) | JRC publication | Recycled-content methodology and chain-of-custody analysis | Technical recommendation may precede or differ from final delegated rules | Very high |
| [[19]](https://doi.org/10.3390/recycling10040122) | DOI-linked peer-reviewed prospective study | 2050 secondary-lithium supply context | Concerns recycled supply contribution, not chemistry-specific plant transfer | High |
| [[22]](https://environment.ec.europa.eu/news/new-law-more-sustainable-circular-and-safe-batteries-enters-force-2023-08-17_en) | European Commission official policy source | Life-cycle framework, collection, due diligence and sustainability provisions | Summary page may not capture every legal exemption or amended deadline | Very high |
| [[25]](https://environment.ec.europa.eu/news/battery-related-waste-codes-update-set-boost-circular-economy-2025-03-05_en) | European Commission official source | 2025 waste-list update and black-mass classification | Waste-shipment application remains fact-specific | Very high |

## Conclusion

No single recycling route is optimal across LFP, LMFP and NMC.

NMC has the clearest near-term recovery case because nickel and cobalt are valuable, strongly regulated and recoverable through mature hydro or combined processing. Its central weakness remains lithium and, in some routes, manganese recovery.

LFP can achieve high lithium extraction, but a credible circular process must also demonstrate what happens to iron and phosphorus. Selective leaching is attractive only when the retained FePO₄ becomes a qualified product rather than a discarded residue. Direct regeneration may preserve greater value, but only with controlled feed and stringent product qualification.

LMFP requires the greatest caution. Its intrinsic elements are Li, Mn, Fe and P; Ni and Co are N/A. Direct spent-LMFP evidence is not yet broad enough to support universal industrial transfer coefficients. Until representative plant balances exist, LMFP planning should use transparent LFP-family analogues, explicit manganese assumptions and wider uncertainty.

For procurement and compliance, the decisive requirement is a reconciled chain from battery input to final qualifying product. Leaching percentages, alloy recovery, black-mass production, product purity, EU recycling efficiency and elemental material recovery are different metrics. A decision-grade recycling contract must keep them different.

---

## References

1. <https://publications.jrc.ec.europa.eu/repository/handle/JRC129861>
2. <https://pubs.rsc.org/en/content/articlehtml/2023/su/d3su00142c>
3. <https://www.mdpi.com/2313-0105/11/1/33>
4. <https://www.oaepublish.com/articles/energymater.2023.57>
5. <https://pubmed.ncbi.nlm.nih.gov/41946108/>
6. <https://www.sciencedirect.com/science/article/abs/pii/S221499372300060X>
7. <https://pmc.ncbi.nlm.nih.gov/articles/PMC13224291/>
8. <https://pubs.rsc.org/en/content/articlehtml/2026/sc/d6sc03686d>
9. <https://environment.ec.europa.eu/news/new-rules-boost-recycling-efficiency-waste-batteries-2025-07-04_en>
10. <https://eur-lex.europa.eu/EN/legal-content/summary/sustainability-rules-for-batteries-and-waste-batteries.html>
11. <https://eur-lex.europa.eu/legal-content/uk/LSU/?uri=CELEX%3A32023R1542>
12. <https://revivebatts.com/battery-recycling-efficiency-eu-2026/>
13. <https://environment.ec.europa.eu/document/download/6297f987-49f6-432b-8119-d60fb6a26c9b_en?filename=COM_2026_470_1_EN_ACT_part1_v3.pdf>
14. <https://www.sciopen.com/local/article_pdf/10.1002/eem2.12863.pdf>
15. <https://www.nature.com/articles/s41598-024-61569-3>
16. <https://www.sciencedirect.com/science/article/pii/S0892687524004667>
17. <https://www.sciencedirect.com/science/article/abs/pii/S2352152X24034182>
18. <https://pmc.ncbi.nlm.nih.gov/articles/PMC10180280/>
19. <https://doi.org/10.3390/recycling10040122>
20. <https://pubmed.ncbi.nlm.nih.gov/41552450/>
21. <https://pdfs.semanticscholar.org/c661/a55033618d5da0fccea635908bea89585d7f.pdf>
22. <https://environment.ec.europa.eu/news/new-law-more-sustainable-circular-and-safe-batteries-enters-force-2023-08-17_en>
23. <https://publications.jrc.ec.europa.eu/repository/handle/JRC146717>
24. <https://publications.jrc.ec.europa.eu/repository/handle/JRC141200>
25. <https://environment.ec.europa.eu/news/battery-related-waste-codes-update-set-boost-circular-economy-2025-03-05_en>
26. <https://www.sciencedirect.com/science/article/pii/S1383586625044442>
