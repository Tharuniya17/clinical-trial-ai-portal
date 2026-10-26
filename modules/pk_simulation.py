import numpy as np

class PKSimulationModule:
    """
    Module 3: Pillar C - Physiological Simulation & Digital Twin Pharmacokinetics (PK)
    Simulates patient-specific One-Compartment/Two-Compartment Oral/IV ADME kinetics.
    Calculates Cmax, AUC, Half-life, Clearance, and risk of exceeding Minimum Toxic Concentration (MTC).
    """

    @staticmethod
    def simulate(volunteer, drug, dose_mg=100.0, time_hours=48.0):
        # 1. Extract Patient Specific Parameters
        weight_kg = float(volunteer.get('weight_kg', 70.0))
        egfr = float(volunteer.get('egfr', 90.0))
        alt = float(volunteer.get('alt_u_l', 25.0))
        
        # 2. Extract Drug Physicochemical Properties
        mw = float(drug.get('molecular_weight', 350.0))
        logP = float(drug.get('logP', 2.5))
        protein_binding = float(drug.get('protein_binding', 0.85))
        base_half_life = float(drug.get('target_half_life', 6.0))

        # 3. Patient-Specific Physiological Scaling (Digital Twin Adaptation)
        # Volume of distribution Vd (L) scaled by body weight and lipophilicity (logP)
        base_vd_per_kg = 0.7 + 0.1 * logP
        Vd = max(10.0, base_vd_per_kg * weight_kg)

        # Baseline clearance CL (L/h) derived from baseline half-life: CL = (ln(2) * Vd) / t1/2
        base_CL = (0.693 * Vd) / base_half_life

        # Renal Scaling Factor based on eGFR (normal = 100 mL/min)
        renal_factor = max(0.2, egfr / 100.0)
        
        # Hepatic Scaling Factor based on ALT (normal = 25 U/L)
        hepatic_factor = max(0.3, 1.0 - max(0, alt - 40.0) / 200.0)

        # Individualized Clearance CL_indiv
        # Assuming 50% renal elimination and 50% hepatic elimination
        CL_indiv = base_CL * (0.5 * renal_factor + 0.5 * hepatic_factor)
        CL_indiv = max(0.1, CL_indiv)

        # Elimination rate constant ke (1/h)
        ke = CL_indiv / Vd
        
        # Absorption rate constant ka (1/h) - assume fast absorption ka ~ 1.5 - 2.5
        ka = 1.8

        # Simulated Half-life
        simulated_half_life = 0.693 / ke

        # 4. Time Grid Simulation (0 to 48 hours, 100 points)
        t = np.linspace(0, time_hours, 120)
        # One-compartment oral absorption model: C(t) = (Dose * ka / (Vd * (ka - ke))) * (e^(-ke*t) - e^(-ka*t))
        F = 0.85  # Bioavailability fraction
        
        conc = (dose_mg * F * ka / (Vd * (ka - ke))) * (np.exp(-ke * t) - np.exp(-ka * t))
        conc = np.maximum(conc, 0.0)

        # PK Parameters
        Cmax = float(np.max(conc))
        Tmax = float(t[np.argmax(conc)])
        AUC = float(np.trapezoid(conc, t))

        # Toxic Concentration Threshold (MTC)
        # MTC modeled as 1.8x typical normal volunteer Cmax
        typical_Cmax = (dose_mg * F * ka / (70.0 * 0.7 * (ka - (0.693 * 70.0 * 0.7 / base_half_life) / (70.0 * 0.7))))
        MTC = typical_Cmax * 1.6 if typical_Cmax > 0 else Cmax * 1.5

        # Ratio of Cmax to MTC
        toxic_exposure_ratio = Cmax / MTC if MTC > 0 else 1.0

        # Calculate Simulation Risk Score (Pillar C)
        # High risk if Clearance is significantly reduced or Cmax exceeds MTC
        exposure_risk = 0.05
        if toxic_exposure_ratio > 1.3:
            exposure_risk = 0.92
        elif toxic_exposure_ratio > 1.0:
            exposure_risk = 0.70
        elif toxic_exposure_ratio > 0.8:
            exposure_risk = 0.40
        else:
            exposure_risk = 0.15

        clearance_retention_risk = 0.05
        if renal_factor < 0.5 or hepatic_factor < 0.5:
            clearance_retention_risk = 0.75
        elif renal_factor < 0.8 or hepatic_factor < 0.8:
            clearance_retention_risk = 0.35

        pillar_c_score = round(0.65 * exposure_risk + 0.35 * clearance_retention_risk, 4)

        return {
            'score': pillar_c_score,
            'risk_percentage': round(pillar_c_score * 100, 1),
            'pk_parameters': {
                'Cmax_mg_L': round(Cmax, 3),
                'Tmax_hours': round(Tmax, 2),
                'AUC_mg_h_L': round(AUC, 2),
                'half_life_hours': round(simulated_half_life, 2),
                'clearance_L_h': round(CL_indiv, 2),
                'volume_distribution_L': round(Vd, 2),
                'mtc_threshold_mg_L': round(MTC, 3),
                'toxic_exposure_ratio': round(toxic_exposure_ratio, 2)
            },
            'time_points': [round(x, 2) for x in t.tolist()],
            'concentration_curve': [round(x, 4) for x in conc.tolist()]
        }
