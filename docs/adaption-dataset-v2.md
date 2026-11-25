# Adaption dataset v2: extraction of Indian health-claim rejection letters

## What v1 taught us (1,000 rows, checked with `tools/validate_dataset.py`)

| Problem in v1 | Rows | Fix in the v2 description |
| --- | --- | --- |
| Input was an instruction ("Please generate a letter… the tone should be…"), not a letter | 374 (37%) | Says plainly that the prompt field *is* the letter, with forbidden phrases listed |
| Quotes in the answer not found word for word in the input | 419 | Quotes must be copied character for character from the input; one rule, repeated in the checklist |
| Output dates not YYYY-MM-DD (e.g. 10-Feb-2025) | 477 | Input dates in any Indian style; output dates always YYYY-MM-DD |
| Few Tamil (5%) and Hindi (3%) letters | 82 | Fixed quotas, with the script named |
| Imbalanced reasons (fraud 4%, waiting period 14%) | | Exactly 100 rows per reason |
| Real insurer names (one appeared 50 times) and off-topic banks/RBI | 50+ | A list of fictional insurers to rotate; banking terms forbidden |
| Letters short and uniform (median 103 words, max 271) | | Attribute grid: format, length, OCR noise, channel, author |

Adaption scores for v1: quality 7.6 (grade B), percentile 15.3, diversity 0.12. Clean rows under the checker: 374 of 1,000.

The description below follows attribute-conditioned generation (AttrPrompt, Yu et al., NeurIPS 2023): list each dimension of variety with its values and combine them at random, instead of asking for "diversity".

## The description to paste into Invent a Dataset

Dataset type: Instruction dataset. Modality: Text. Rows: 1,000.

```text
TASK: Teach a model to read an Indian health insurance claim rejection letter and return its key facts as JSON.

EACH ROW
- PROMPT = the complete text of ONE rejection letter or rejection message exactly as the policyholder received it. Nothing else: no instructions, no notes, no description of the letter, no "Here is a letter". It must never contain phrases such as "Please generate", "Write a", "The letter should", "The tone should", "Use formal Indian English" or "The ground is".
- COMPLETION = only a JSON object with exactly these 11 keys, in this order:
  insurer_name, policy_number, policy_inception_date, claim_type, claim_amount_inr, admission_date, discharge_date, diagnosis, rejection_ground, clause_cited, rejection_reason_quote

FIELD RULES
- Use null when the letter does not state a fact. Never invent a value that is not in the letter.
- policy_number: the policy number only, never the claim number or the TPA reference.
- claim_type: "cashless", "reimbursement" or "partial_settlement".
- claim_amount_inr: an integer in rupees (246500, not "Rs. 2,46,500").
- Dates in the COMPLETION: always YYYY-MM-DD, whatever style the letter uses.
- rejection_ground: exactly one of non_disclosure_proposal, pre_existing_disease, waiting_period, hospitalisation_not_justified, treatment_not_covered, amount_limited, documents_not_submitted, policy_not_in_force, excluded_by_clause, fraud_misrepresentation.
- clause_cited and rejection_reason_quote: copied CHARACTER FOR CHARACTER from the PROMPT (same words, spelling, punctuation and capitals). They must be findable in the letter by exact text search. clause_cited is null if the letter cites no clause.

BALANCE: exactly 100 rows per rejection_ground.

VARY EACH LETTER BY RANDOMLY COMBINING ONE VALUE FROM EACH LIST (do not fix any attribute):
- Insurer (all fictional, rotate evenly): Suraksha General, Arogya Bharat Health, Kaveri Health Insurance, Navjeevan General, Sahyadri Health Assurance, Ganga Mutual General, Deccan Care Health, Himalaya Health Insurance, Vindhya General, Nilgiri Health Co., Konark General, Sindhu Health Assurance. Never use the name of a real Indian insurer.
- Issued by: insurer claims department / third-party administrator (TPA) on the insurer's behalf / hospital insurance desk forwarding the decision.
- Channel and format: formal letter on letterhead / email / TPA portal status message / SMS-style summary (40-60 words) / text from a scanned letter with OCR noise (broken lines, a hyphen splitting a word across lines, stray characters, a missing space).
- Length: 40-80, 80-200, 200-400 words (one third each).
- Claim type: cashless pre-authorisation denial / reimbursement rejection / partial settlement with deductions.
- Treatment: cardiac (angioplasty, bypass), maternity, orthopaedic (knee replacement, fracture), cancer (chemotherapy), dengue or typhoid, cataract, dialysis, appendicitis or gallbladder, mental health admission, AYUSH treatment, day-care procedure, COVID or pneumonia.
- City: spread across at least 25 Indian cities and towns, including tier-2 and tier-3 (e.g. Madurai, Nagpur, Guwahati, Ranchi, Vijayawada, Mysuru, Bhubaneswar, Dehradun, Siliguri, Thrissur).
- Amount: Rs 8,000 to Rs 15,00,000, written in varied Indian styles (Rs. 2,46,500 / INR 246500 / ₹2.47 lakh).
- Dates in the letter: varied styles (14/08/2026, 14-Aug-2026, 14th August 2026, 2026-08-14).
- Tone: formal and brief / bureaucratic and long / polite with regret / blunt.
- Language: 70% English only; 15% English with one full paragraph in Tamil script; 15% English with one full paragraph in Hindi (Devanagari script). The quoted fields may come from any language in the letter but must be copied exactly.

REALISM
- Write like real Indian insurer and TPA correspondence: claim numbers, TPA names (fictional), policy clause numbers, "repudiated", "not payable", "inadmissible", references to grievance redressal and the Insurance Ombudsman at the end.
- Include in about 30% of letters facts that make the rejection look weak (a policy renewed for many years, a pre-policy medical check, a missing written reason) so the data reflects contestable rejections.
- Health insurance only: no banks, loans, EMIs, RBI, or life or motor insurance.
- All people, hospitals, policy numbers and claim numbers are fictional.

CHECK EVERY ROW BEFORE OUTPUT
1. The PROMPT is a letter a policyholder could receive, with no instructions in it.
2. clause_cited and rejection_reason_quote appear in the PROMPT exactly, character for character.
3. All COMPLETION dates are YYYY-MM-DD; missing facts are null.
4. The JSON has exactly the 11 keys and nothing outside it.
```

## After generation

```bash
python tools/validate_dataset.py indian_health_rejections_v2.csv
```

Targets: at least 90% clean, every reason 80 to 120 rows, at least 10% Tamil and 10% Hindi rows, and Adaption's diversity score above v1's 0.12.
