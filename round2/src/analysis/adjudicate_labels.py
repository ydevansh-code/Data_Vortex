import pandas as pd

file_path = "c:/GitHub/Projects/Data_Vortex/round2/reports/label_noise_audit_50.csv"
df = pd.read_csv(file_path)

audits = [
    "model_right", "ambiguous", "label_right", "label_right", "label_right", "label_right", "label_right", 
    "label_right", "label_right", "label_right", "label_right", "label_right", "label_right", "label_right",
    "ambiguous", "ambiguous", "ambiguous", "model_right", "label_right", "label_right", "label_right", 
    "ambiguous", "model_right", "ambiguous", "label_right", "label_right", "label_right", "label_right",
    "label_right", "label_right", "label_right", "label_right", "label_right", "ambiguous", "ambiguous",
    "label_right", "label_right", "ambiguous", "model_right", "model_right", "ambiguous", "label_right",
    "ambiguous", "label_right", "ambiguous", "ambiguous", "label_right", "ambiguous", "model_right", "label_right"
]

df["manual_audit_correct_label"] = audits

model_right = sum(1 for a in audits if a == "model_right")
label_right = sum(1 for a in audits if a == "label_right")
ambiguous = sum(1 for a in audits if a == "ambiguous")

noise_rate = (model_right + ambiguous) / len(audits)

print(f"model_right: {model_right}")
print(f"label_right: {label_right}")
print(f"ambiguous: {ambiguous}")
print(f"Estimated Label Noise / Irreducible Error Rate: {noise_rate * 100:.1f}%")

df.to_csv(file_path, index=False)
