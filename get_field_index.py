import pickle
import re
def get_lst_derived_type(map_field):
    with open('field_index.txt', 'r') as field_:
        fields_=field_.readlines()
    for line in fields_:
        field=re.match("(\s*)\'([A-Z0-9_%]+)\'.+\'(.+)\'", line)
        regex="([A-Z]+\s*\(KIND\=[A-Z]+\))(\s:+\s)([A-Z]+.+)"
        if field:
            match1=re.match(regex,field.group(3)).group(1)
            match2=re.match(regex, field.group(3)).group(3)
            #match1=REAL(KIND=JPRB)
            #match2=DM(:,:)
            d = match2.count(":")
            print(f"{match1=}")
            print(f"{match2=}")
            print(f"{d=}")
            map_field[field.group(2)]=[match1, match2]
            #map_field[field.group(2)]=[match1, match2, d]
#TODO : create third entry with the dim (number of ':' + 1) and replace the second entry by the name directly instead of name(:,:,:)

            #map_field[field.group(1)]=[re.match(regex,field.group(2)).group(1), re.match(regex, field.group(2)).group(3)]
        #fields[field.group(1)]=[re.match(regex,field.group(2)).group(1), re.match(regex, field.group(2)).group(3)]
        #field['SURFACE_VARIABLES%GSD_VD%VCAPE%T1']=['REAL(KIND=JPRB)',T1(:)]

map_field={} #dict associating A%B%C with C type and dim. 
get_lst_derived_type(map_field)
with open('field_index.pkl', 'wb') as fp:
    pickle.dump(map_field, fp)
    print('dictionary ', map_field, ' saved successfully to file')

with open("field_index.pkl", 'rb') as fp:
    map_test = pickle.load(fp)
