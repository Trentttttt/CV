
from main import *

start_from(r'C:\Users\13471\Desktop\实证')
a = pd.read_excel(r'C:\Users\13471\Desktop\bylw\数据\自变量\指数收盘价.xlsx',index_col='日期')['上证50']
c = pd.date_range('2000-01-28','2021-04-24', freq='M')
a.index = c
a = a.dropna()
X13PATH = r'C:\Users\13471\Downloads\2_35d01083886a123d42577a92b4352e08_winx12\WinX12\x12a\x12a.exe'
bunch = sm.tsa.x13_arima_analysis(a, x12path=X13PATH)
bunch.seasadj

