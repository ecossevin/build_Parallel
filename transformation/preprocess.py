
def get_preprocess_pragma(src):
    new_lines = []
    with open(src, 'r', encoding='utf-8') as f2:
        lines = f2.readlines()
        for line in lines:
            if '!$ACDC PARALLEL' in line:
                line = line.replace('!$ACDC PARALLEL', '!$loki parallel PARALLEL')
                line = line.replace('{', '')
                
            elif '!$ACDC }' in line:
                line = line.replace('!$ACDC }', '!$loki end parallel')

            elif '!$ACDC {' in line:
                line = line.replace('ACDC {', '') #if ACDC pragma is on multiple lines


            new_lines.append(line)
    return new_lines
