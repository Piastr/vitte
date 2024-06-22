import xlrd
import datetime
import os


def get_lessons(faculty, course, group):
    months = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь", "ноябрь",
              "декабрь"]

    current_date = datetime.datetime.now()
    current_month = current_date.month

    rb = xlrd.open_workbook(f'lessons/{faculty} очная {months[current_month - 1]}.xls', formatting_info=True)

    sheet = rb.sheet_by_index(0)


def get_group(faculty, course):
    files = os.listdir('lessons')
    old_file = [f for f in files if "old" in f.lower() and faculty in f and f.endswith('.xls')]
    print(old_file)
    file_path = os.path.join('lessons', old_file[0])
    workbook = xlrd.open_workbook(file_path)
    try:
        sheet = workbook.sheet_by_name(f'{str(course)} курс')
    except:
        sheet = workbook.sheet_by_name(f'{str(course)} курс ')
    groups = []
    for i in range(6):
        try:
            group_name = sheet.cell_value(16, 3 + i).strip()
            group_name = group_name.split('\n')[0]
            groups.append(group_name)
        except:
            continue
    print(groups)

    return groups


if __name__ == '__main__':
    # get_lessons('ФИТ', 2, 4)
    get_group('ФИТ', "2")
