cases = []

with open('combined_list.csv', 'r') as infile:
    for line in infile:
        cases.append(line)

unique_cases = set(cases)

with open('fixed_combined.txt', 'w') as outf:
    for case in unique_cases:
        outf.write(case)