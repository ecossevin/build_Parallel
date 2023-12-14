import pickle
import re
def get_lst_derived_type(map_field):
    with open('field_index.txt', 'r') as field_:
        fields_=field_.readlines()
    for line in fields_:
        field=re.match("(\s*)\'([A-Z0-9_%]+)\'.+\'(.+)\'", line)
        regex="([A-Z]+\s*\(KIND\=[A-Z]+\))(\s:+\s)([A-Z]+.+)"
        #field.group(1)='          '
        #field.group(2)='FIELD_VARIABLES%CSPNL%DM'
        #field.group(3)='REAL(KIND=JPRB) :: DM(:,:)'
        if field:
#            print("field match")
#            print("field=",field)
#            print("fg3=",field.group(3))
            match1=re.match(regex,field.group(3)).group(1)
            match2=re.match(regex, field.group(3)).group(3)
            #match1=REAL(KIND=JPRB)
            #match2=DM(:,:)
            map_field[field.group(2)]=[match1, match2]

            #map_field[field.group(1)]=[re.match(regex,field.group(2)).group(1), re.match(regex, field.group(2)).group(3)]
        #fields[field.group(1)]=[re.match(regex,field.group(2)).group(1), re.match(regex, field.group(2)).group(3)]
        #field['SURFACE_VARIABLES%GSD_VD%VCAPE%T1']=['REAL(KIND=JPRB)',T1(:)]
map_field={} #dict associating A%B%C with C type and dim. 
get_lst_derived_type(map_field)
with open('field_index.pkl', 'wb') as fp:
    pickle.dump(map_field, fp)
    print('dictionary ', map_field, ' saved successfully to file')
