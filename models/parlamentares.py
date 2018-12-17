from datetime import timedelta

class ParlamentaresApp():

    def __init__(self):
        self.periodo = {'days': 7}
    
    def obterDataInicial(self, data_final, **kwargs):
        return data_final - timedelta(**kwargs)


    def formatarDatasYMD(self, *args):
        resultado = ()
        for data in args:
            try:
                resultado += ('{}-{:02d}-{:02d}'.format(
                    data.year,
                    data.month,
                    data.day),)
            except Exception as e:
                print(e)
        return resultado

        
    def obterDataInicialEFinal(self, data_final):
        data_inicial = self.obterDataInicial(data_final, **self.periodo)
        return self.formatarDatasYMD(data_inicial, data_final)


    def setPeriodoDias(self, periodo_dias):
        try:
            if int(periodo_dias) in range(7, 29):
                self.periodo['days'] = int(periodo_dias)
        except ValueError:
            periodo_dias = 7