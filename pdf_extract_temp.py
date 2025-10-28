from pdfminer.high_level import extract_text
p = r'predict-model-with-taxi/T-drive Taxi Trajectories/release/user_guide.pdf'
text = extract_text(p)
lines = text.splitlines()
for line in lines[:250]:
    print(line.encode('ascii', errors='ignore').decode('ascii'))
