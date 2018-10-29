from datetime import timedelta

class ParlamentaresApp():

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
        data_inicial = self.obterDataInicial(data_final, weeks=1)
        return self.formatarDatasYMD(data_inicial, data_final)
