def cleanline(line):
    fields = line.split(',')
    output = ""
    if len(fields[0]) == 0:
        output = "N\A,"
    else:
        output = fields[0]+','
    
    output+=fields[1]+',' + '"'
    for i in range(2, len(fields)-1):
        output+=fields[i] + ','
    output = output[:-1]
    output+='"' + ',' + fields[-1]
    return output

def reparse(input_file, output_file):
    with open(input_file, 'r') as in_f:
        with open(output_file, 'w') as out_f:
            for line in in_f:
                out_f.write(cleanline(line))

"""
11/05/1962,11665,"Animal: Animal Unattended in Vehicle 1st Offense",08/29/2018
11/05/1962,11666,"Animal: Animal Unattended in Vehicle 1st Offense",08/29/2018
"""
def find_missing(case_file, output_file):
    raw_casenums = []
    loaded_casenums = set()
    with open(case_file, 'r') as cs:
        for line in cs:
            raw_casenums.append(line.strip('\n'))
    with open(output_file, 'r') as out_f:
        for line in out_f:
            flds = line.split(',')
            loaded_casenums.add(flds[1])
            # print(flds[1])
    for case in raw_casenums:
        if case not in loaded_casenums:
            pass
            print(case)

if __name__ == "__main__":
    reparse("reinstatment_scrape copy.csv", "fixed_lines.csv")
    # find_missing("casenums.csv", "fixed_lines.csv") 