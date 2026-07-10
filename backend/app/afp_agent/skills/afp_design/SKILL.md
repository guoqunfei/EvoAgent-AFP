---
name: afp-design
description: Antifreeze protein sequence design principles for enhanced ice-binding activity
version: 1.0.0
category: afp_design
---

# AFP Design Skill — Ice-Binding Surface Engineering

## TH Optimization Rules
1. Maintain precise Thr spacing matching target ice plane (4.5Å prism, 7.4Å basal, 16.5Å pyramidal)
2. Keep IBS flat (RMSD < 1Å) — no bulky residues (F/W/Y/R/K) on IBS
3. Consider β-helix scaffold for hyperactivity (TH > 2°C)
4. Engineer disulfide bonds for scaffold rigidity
5. G63S-type mutations can boost activity 40% by restoring local H-bond network

## IRI Optimization Rules
1. Maximize IBS surface area for better ice crystal coverage
2. Incorporate Asn-Thr pairs for plant-type ice binding
3. Consider bacterial DUF3494 scaffold for high IRI at low concentration
4. Multimerization can enhance IRI 50-fold
5. Geometric complementarity alone drives measurable IRI (de novo iTHR: 0.97 µM vs wt 4.6 µM)

## Stability Rules
1. Preserve all disulfide bond pairs (Cys mutations in pairs only)
2. Maintain hydrophobic core packing
3. Add helix-capping residues for α-helical AFPs
4. Type III β-sandwich: N14/T18/Q44 are ESSENTIAL — never mutate

## Expression Optimization
1. Non-IBS face tolerates extensive mutation
2. MBP/GST fusion tags improve yield 2-10x
3. TAT fusion enables intracellular delivery for cell cryopreservation
4. Optimize codon usage for P. pastoris (preferred host for disulfide-rich AFPs)

## Safety Design
1. Avoid known immunogenic sequence motifs
2. Keep net charge moderate (|charge| < 1 at neutral pH)
3. Minimize hydrophobic patches to reduce aggregation
4. Test hemolytic activity for any blood-contact applications

## Pitfalls
- DO NOT mutate IBS Thr residues — spacing match is critical
- DO NOT introduce charged residues (D/E/K/R) on IBS — repel ice surface
- DO NOT break disulfide pairs — scaffold rigidity is essential for hyperactivity
- Avoid large hydrophobic patches — cause aggregation in recombinant expression
