# Arogya Sanjeevani Policy, Niva Bupa Health Insurance Co. Ltd. - key clauses for claim disputes

Insurer: Niva Bupa Health Insurance Company Limited. UIN: NBHHLIP27056V042627. Policy wording file: knowledge-base/policy-wordings/arogya-sanjeevani-niva-bupa-2026-27.pdf. Source: https://transactions.nivabupa.com/pages/doc/policy_wording/ArogyaSanjeevani-PolicyDocument.pdf?v=1.0

Arogya Sanjeevani is an IRDAI-mandated standard product, but insurers' wordings still differ on some clauses (e.g. which expenses the room-rent proportionate deduction applies to). Always judge a claim against the claimant's own insurer wording. Figures below were extracted on 2026-09-17.

## Limits

```json
{
  "sum_insured_range_inr": [
    50000,
    1000000
  ],
  "room_rent_per_day": {
    "pct_of_sum_insured": 2,
    "max_inr": 5000
  },
  "icu_iccu_per_day": {
    "pct_of_sum_insured": 5,
    "max_inr": 10000
  },
  "cataract_per_eye_per_year": {
    "pct_of_sum_insured": 25,
    "max_inr": 40000,
    "rule": "whichever is lower"
  },
  "modern_treatments": {
    "pct_of_sum_insured": 50,
    "procedures": [
      "Uterine Artery Embolization and HIFU",
      "Balloon Sinuplasty",
      "Deep Brain Stimulation",
      "Oral Chemotherapy",
      "Immunotherapy - Monoclonal Antibody to be given as injection",
      "Intra Vitreal Injections",
      "Robotic Surgeries",
      "Stereotactic Radio Surgeries",
      "Bronchical Thermoplasty",
      "Vaporisation of the Prostrate (Green Laser treatment or Holmium Laser Treatment)",
      "IONM (Intra Operative Neuro Monitoring)",
      "Stem Cell Therapy: Hematopoietic stem cells for bone marrow transplant for haematological conditions"
    ]
  },
  "road_ambulance_per_hospitalisation_inr": 2000,
  "co_payment_pct": 5,
  "pre_hospitalisation_days": 30,
  "post_hospitalisation_days": 60,
  "cumulative_bonus": {
    "pct_per_claim_free_year": 5,
    "max_pct_of_sum_insured": 50
  },
  "ayush": "up to sum insured"
}
```

## Proportionate (pro-rata) deduction

Applies to: room rent, nursing charges, medical practitioners' fees, operation theatre charges.
Does not apply to: medicines and drugs / pharmacy, diagnostics / investigations, implants and surgical appliances, consumables billed outside the listed heads.
Clause: Section 4.1, Note 2, page 6.

## Room rent and ICU limits (Section 4.1(i)-(ii), page 6)

> Room Rent, Boarding, Nursing Expenses as provided by the Hospital/ Nursing Home up to 2% of the sum insured subject to maximum of Rs.5000/- per day. ii. Intensive Care Unit (ICU) / Intensive Cardiac Care Unit (ICCU) expenses up to 5% of sum insured subject to maximum of Rs. 10,000/- per day.

Use when: Checking whether room / ICU charges were capped correctly.
Citation id: NIVA-AS-4.1-ROOM

## Proportionate deduction limited to associated medical expenses (Section 4.1, Note 2, page 6)

> If the Insured Person is admitted in a room / ICU / ICCU at rates exceeding the aforesaid limits, then We shall be liable to pay only a pro-rated portion of the total Associated Medical Expenses (including surcharge or taxes thereon) as per the following formula: (eligible Room limit / Room Rent actually incurred) * total Associated Medical Expenses Associated Medical Expenses shall include Room Rent, nursing charges, Medical Practitioners' fees and operation theatre charges

Use when: Insurer applied a proportionate / pro-rata deduction to pharmacy, diagnostics, implants or other heads outside room rent, nursing, doctor fees and OT charges - challengeable.
Citation id: NIVA-AS-4.1-PRORATA

## 24-hour rule does not apply to day care (Section 4.1.1, Note 1, page 6)

> Expenses of Hospitalization for a minimum period of 24 consecutive hours only shall be admissible. However, the time limit shall not apply in respect of Day Care Treatment.

Use when: Claim rejected for hospitalisation under 24 hours - check whether the treatment is day care.
Citation id: NIVA-AS-4.1-24H

## Cataract sub-limit (Section 4.3, page 6)

> The Company shall indemnify medical expenses incurred for treatment of Cataract, subject to a limit of 25% of Sum Insured or Rs. 40,000/-, whichever is lower, per each eye in one policy year.

Use when: Cataract claim capped - verify the cap was computed per eye using the lower of 25% SI or Rs 40,000.
Citation id: NIVA-AS-4.3-CATARACT

## Modern treatments covered up to 50% of sum insured (Section 4.6, page 7)

> The following procedures will be covered (wherever medically indicated) either as inpatient or as part of day care treatment in a hospital up to 50% of Sum Insured, specified in the policy schedule, during the policy period:

Use when: Robotic surgery, oral chemotherapy, immunotherapy, intra-vitreal injections etc. rejected or capped below 50% of SI.
Citation id: NIVA-AS-4.6-MODERN

## Non-payable and subsumed items lists (Section 4.7, page 7)

> The expenses that are not covered in this policy are placed under List-I of Annexure-A. The list of expenses that are to be subsumed into room charges, or procedure charges or costs of treatment are placed under List-II, List-III and List-IV of Annexure-A respectively.

Use when: Checking a line item deducted as non-payable.
Citation id: NIVA-AS-4.7-LISTS

## Pre-existing disease waiting period 36 months (Section 6.1 (Code Excl01), page 8)

> Expenses related to the treatment of a pre-existing Disease (PED) and its direct complications shall be excluded until the expiry of 36 months of continuous coverage after the date of inception of the first policy.

Use when: Claim rejected as PED - compute months of continuous coverage (including portability) at date of admission.
Citation id: NIVA-AS-6.1-PED

## Specific waiting periods do not apply to accidents (Section 6.3 (Code Excl02), page 8)

> Expenses related to the treatment of the following listed conditions, surgeries/treatments shall be excluded until the expiry of 24/36 months of continuous coverage, as may be the case after the date of inception of the first policy with the insurer. This exclusion shall not be applicable for claims arising due to an accident.

Use when: Claim for a listed condition rejected under waiting period - check coverage months and whether it arose from an accident.
Citation id: NIVA-AS-6.3-SPECIFIC

## Admission primarily for diagnostics excluded (Section 7.1 (Code Excl04), page 9)

> Expenses related to any admission primarily for diagnostics and evaluation purposes.

Use when: Claim rejected as 'admission only for investigation' - check if active treatment was given.
Citation id: NIVA-AS-7.1-EVAL

## Moratorium after sixty continuous months (Section 8, page 11)

> After completion of sixty continuous months of coverage (including portability and migration) in health insurance policy, no policy and claim shall be contestable by the insurer on the grounds of non-disclosure, misrepresentation, except on grounds of established fraud.

Use when: Claim rejected for non-disclosure / misrepresentation after 60+ months of continuous cover - strong challenge unless fraud is established.
Citation id: NIVA-AS-8-MORATORIUM

## Cashless discharge within three hours (Section 9.1(vi), page 12)

> Once the final authorization request is received for discharge, the same will be processed within three hours from the final documents received. In case of delay from our end, any additional amount charged by the hospital will be borne by us. This amount will be paid over and above the policy limits.

Use when: Hospital charged extra room rent because final cashless approval was delayed.
Citation id: NIVA-AS-9.1-DISCHARGE

## Insured pays non-medical and inadmissible expenses at discharge (Section 9.1(iv), page 12)

> At the time of discharge, the insured person has to verify and sign the discharge papers, pay for non-medical and inadmissible expenses.

Use when: Explaining why some genuinely non-payable items were collected from the patient.
Citation id: NIVA-AS-9.1-NONMEDICAL

## Claim notification timelines (Section 9.3, page 12)

> Within 24hours from the date of emergency hospitalization required or before the Insured Person's discharge from Hospital, whichever is earlier. ii. At least 48 hours prior to admission in Hospital in case of a planned Hospitalization.

Use when: Claim rejected or reduced for late intimation.
Citation id: NIVA-AS-9.3-NOTIFY

## Delay can be condoned (Section 9.4, Note 3, page 13)

> Any delay in notification or submission may be condoned on merit where delay is proved to be for reasons beyond the control of the Insured Person.

Use when: Claim rejected only for delayed intimation or document submission - challengeable if the delay had a genuine reason (emergency, ICU stay, etc.).
Citation id: NIVA-AS-9.4-CONDONE

## 5% co-payment on admissible amount (Section 9.5, page 13)

> Each and every claim under the Policy shall be subject to a Copayment of 5% applicable to claim amount admissible and payable as per the terms and conditions of the Policy.

Use when: Checking co-pay was computed on the admissible amount (after other deductions), not on the gross bill.
Citation id: NIVA-AS-9.5-COPAY

## Settle or reject within 15 days, else penal interest (Section 9.6, page 13)

> The Company shall settle or reject a claim, as the case may be, within 15 days from the claim submission date. ii. ln the case of delay in the payment of a claim, the Company shall be liable to pay interest from the date of receipt of claim intimation till the date of payment of claim at a rate of 2% above the bank rate.

Use when: Claim decision delayed - demand interest.
Citation id: NIVA-AS-9.6-SETTLEMENT

## No repudiation for fraud where misstatement was bona fide (Section 10.9, page 15)

> The Company shall not repudiate the claim and / or forfeit the policy benefits on the ground of Fraud, if the insured person / beneficiary can prove that the misstatement was true to the best of his knowledge and there was no deliberate intention to suppress the fact or that such misstatement of or suppression of material fact are within the knowledge of the insurer.

Use when: Claim rejected alleging fraud / suppression where the insured acted in good faith.
Citation id: NIVA-AS-10.9-FRAUD

## Grievance redressal ladder (Section 11, page 18)

> Grievance may also be lodged at IRDAI integrated Grievance Management System

Use when: Drafting escalation steps.
Citation id: NIVA-AS-11-GRIEVANCE

## Medical expenses limited to locality rates (reasonable & customary basis) (Definition 3.29, page 4)

> Medical Expenses means those expenses that an insured person has necessarily and actually incurred for medical treatment on account of illness or accident on the advice of a medical practitioner, as long as these are no more than would have been payable if the insured person had not been insured and no more than other hospitals or doctors in the same locality would have charged for the same medical treatment.

Use when: Insurer cut a fee as 'not reasonable and customary' - the insurer must show what other hospitals/doctors in the same locality charge for the same treatment.
Citation id: NIVA-AS-3.29-MEDICAL-EXPENSES

## Road ambulance capped at Rs 2,000 (Section 4.1.1(v), page 6)

> Expenses incurred on road Ambulance subject to a maximum of Rs.2000/- per hospitalisation.

Use when: Ambulance charge above Rs 2,000 restricted.
Citation id: NIVA-AS-4.1.1-AMBULANCE

## Hazardous sports exclusion applies only to professionals (Section 7.6 (Code Excl09), page 10)

> Expenses related to any treatment necessitated due to participation as a professional in hazardous or adventure sports

Use when: Injury from sport or adventure activity rejected - exclusion needs professional participation.
Citation id: NIVA-AS-7.6-SPORTS
