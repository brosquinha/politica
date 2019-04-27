import json
from datetime import datetime
from time import time

from flask import render_template, request

from legislei.exceptions import ModelError
from legislei.houses.casa_legislativa import CasaLegislativa
from legislei.models.relatorio import (Evento, Orgao, Parlamentar, Proposicao,
                                       Relatorio)
from legislei.SDKs.CamaraDeputados.entidades import (Deputados, Eventos,
                                                     Proposicoes, Votacoes)
from legislei.SDKs.CamaraDeputados.exceptions import CamaraDeputadosError


class CamaraDeputadosHandler(CasaLegislativa):

    def __init__(self):
        super().__init__()
        self.dep = Deputados()
        self.ev = Eventos()
        self.prop = Proposicoes()
        self.vot = Votacoes()
        self.relatorio = Relatorio()

    def obter_relatorio(self, parlamentar_id, data_final=None, periodo_dias=7):
        try:
            self.relatorio = Relatorio()
            self.relatorio.aviso_dados = u'Dados de votações em sessões não disponíveis.'
            start_time = time()
            if data_final:
                data_final = datetime.strptime(data_final, '%Y-%m-%d')
                print(data_final)
            else:
                data_final = datetime.now()
            self.setPeriodoDias(periodo_dias)
            deputado_info = self.obter_parlamentar(parlamentar_id)
            self.relatorio.data_inicial = self.obterDataInicial(
                data_final, **self.periodo)
            self.relatorio.data_final = data_final
            print('Deputado obtido em {0:.5f}'.format(time() - start_time))
            (
                eventos,
                _presenca_total,
                todos_eventos
            ) = self.procurarEventosComDeputado(
                deputado_info.id,
                data_final
            )
            print('Eventos obtidos em {0:.5f}'.format(time() - start_time))
            orgaos = self.obterOrgaosDeputado(deputado_info.id, data_final)
            print('Orgaos obtidos em {0:.5f}'.format(time() - start_time))
            orgaos_nomes = [orgao['nomeOrgao'] for orgao in orgaos]
            for e in eventos:
                evento = Evento()
                evento.id = str(e['id'])
                evento.data_inicial = e['dataHoraInicio']
                evento.data_final = e['dataHoraFim']
                evento.situacao = e['situacao']
                evento.nome = e['descricao']
                evento.set_presente()
                for o in e['orgaos']:
                    orgao = Orgao()
                    orgao.nome = o['nome']
                    orgao.apelido = o['apelido']
                    evento.orgaos.append(orgao)
                pautas = self.obterPautaEvento(e['id'])
                if pautas == [{'error': True}]:
                    evento.pautas.append(None)
                else:
                    for pauta in pautas:
                        if len(pauta['votacao']):
                            proposicao = Proposicao()
                            if pauta['proposicao_detalhes'] == [{'error': True}]:
                                proposicao = None
                            else:
                                proposicao.id = str(pauta['proposicao_detalhes']['id'])
                                proposicao.tipo = pauta['proposicao_detalhes']['siglaTipo']
                                proposicao.url_documento = \
                                    pauta['proposicao_detalhes']['urlInteiroTeor']
                                proposicao.url_autores = \
                                    pauta['proposicao_detalhes']['uriAutores']
                                proposicao.pauta = pauta['proposicao_detalhes']['ementa']
                            if pauta['votacao'] == [{'error': True}]:
                                proposicao.voto = 'ERROR'
                            else:
                                voto = self.obterVotoDeputado(
                                    pauta['votacao'][0]['id'], deputado_info.id)
                                proposicao.voto = voto
                            evento.pautas.append(proposicao)
                self.relatorio.eventos_presentes.append(evento)
            print('Pautas obtidas em {0:.5f}'.format(time() - start_time))
            (
                eventos_ausentes,
                eventos_ausentes_total,
                _eventos_previstos
            ) = self.obterEventosAusentes(
                deputado_info.id,
                data_final,
                eventos,
                orgaos_nomes,
                todos_eventos
            )
            self.relatorio.eventos_ausentes_esperados_total = eventos_ausentes_total
            for e in eventos_ausentes:
                evento = Evento()
                evento.id = str(e['id'])
                if e['controleAusencia'] == 1:
                    evento.set_ausente_evento_previsto()
                elif e['controleAusencia'] == 2:
                    evento.set_ausencia_evento_esperado()
                else:
                    evento.set_ausencia_evento_nao_esperado()
                evento.data_inicial = e['dataHoraInicio']
                evento.data_final = e['dataHoraFim']
                evento.nome = e['descricao']
                evento.situacao = e['situacao']
                evento.url = e['uri']
                for o in e['orgaos']:
                    orgao = Orgao()
                    orgao.nome = o['nome']
                    orgao.apelido = o['apelido']
                    evento.orgaos.append(orgao)
                self.relatorio.eventos_ausentes.append(evento)
                if evento.presenca > 1:
                    self.relatorio.eventos_previstos.append(evento)
            print('Ausencias obtidas em {0:.5f}'.format(time() - start_time))
            self.obterProposicoesDeputado(deputado_info, data_final)
            print('Proposicoes obtidas em {0:.5f}'.format(time() - start_time))
            
            self.relatorio.data_final = self.relatorio.data_final.strftime("%d/%m/%Y")
            self.relatorio.data_inicial = self.relatorio.data_inicial.strftime("%d/%m/%Y")
            return self.relatorio
        except CamaraDeputadosError:
            raise ModelError("API Câmara dos Deputados indisponível")

    def obterOrgaosDeputado(self, deputado_id, data_final=datetime.now()):
        orgaos = []
        di, df = self.obterDataInicialEFinal(data_final)
        try:
            for page in self.dep.obterOrgaosDeputado(deputado_id, dataInicio=di, dataFim=df):
                for item in page:
                    dataFim = datetime.now()
                    if item['dataFim'] != None:
                        try:
                            # Um belo dia a API retornou Epoch ao invés do formato documentado (YYYY-MM-DD), então...
                            dataFim = datetime.fromtimestamp(item['dataFim']/1000)
                        except TypeError:
                            try:
                                dataFim = datetime.strptime(item['dataFim'], '%Y-%m-%d')
                            except ValueError:
                                #Agora aparentemente ele volta nesse formato aqui... aiai
                                dataFim = datetime.strptime(item['dataFim'], '%Y-%m-%dT%H:%M')
                    if (item['dataFim'] == None or dataFim > data_final):
                        orgao = Orgao()
                        if 'nomeOrgao' in item:
                            orgao.nome = item['nomeOrgao']
                        if 'siglaOrgao' in item:
                            orgao.sigla = item['siglaOrgao']
                        if 'titulo' in item:
                            orgao.cargo = item['titulo']
                        self.relatorio.orgaos.append(orgao)
                        orgaos.append(item)
            return orgaos
        except CamaraDeputadosError:
            return [{'nomeOrgao': None}]

    def procurarEventosComDeputado(self, deputado_id, data_final=datetime.now()):
        eventos_com_deputado = []
        eventos_totais = []
        di, df = self.obterDataInicialEFinal(data_final)
        for page in self.ev.obterTodosEventos(
            dataInicio=di,
            dataFim=df
        ):
            for item in page:
                eventos_totais.append(item)
                for dep in self.ev.obterDeputadosEvento(item['id']):
                    if str(dep['id']) == deputado_id:
                        eventos_com_deputado.append(item)
        if len(eventos_totais) == 0:
            presenca = 0
        else:
            presenca = 100*len(eventos_com_deputado)/len(eventos_totais)
        return eventos_com_deputado, presenca, eventos_totais

    def obterEventosPrevistosDeputado(self, deputado_id, data_final):
        di, df = self.obterDataInicialEFinal(data_final)
        eventos = []
        try:
            for page in self.dep.obterEventosDeputado(
                deputado_id,
                dataInicio=di,
                dataFim=df
            ):
                for item in page:
                    eventos.append(item)
            return eventos
        except CamaraDeputadosError:
            return [{'id': None}]

    def obterPautaEvento(self, ev_id):
        try:
            pautas = self.ev.obterPautaEvento(ev_id)
            if not pautas:
                return []
            pautas_unicas = []
            pautas_unicas_ids = []
            for p in pautas:
                proposicao_id = p['proposicao_']['id']
                if proposicao_id not in pautas_unicas_ids and proposicao_id != None:
                    pautas_unicas_ids.append(proposicao_id)
                    pautas_unicas.append(p)
                    try:
                        p['proposicao_detalhes'] = self.prop.obterProposicao(
                            proposicao_id)
                    except CamaraDeputadosError:
                        p['proposicao_detalhes'] = [{'error': True}]
                    try:
                        p['votacao'] = self.prop.obterVotacoesProposicao(
                            proposicao_id)
                    except CamaraDeputadosError:
                        p['votacao'] = [{'error': True}]
            return pautas_unicas
        except CamaraDeputadosError:
            return [{'error': True}]

    def obterVotoDeputado(self, vot_id, dep_id):
        try:
            for page in self.vot.obterVotos(vot_id):
                for v in page:
                    if str(v['parlamentar']['id']) == dep_id:
                        return v['voto']
        except CamaraDeputadosError:
            return False

    def obterEventosAusentes(
            self,
            dep_id,
            data_final,
            eventos_dep,
            orgaos_dep,
            todos_eventos
    ):
        demais_eventos = [x for x in todos_eventos if x not in eventos_dep]
        eventos_previstos = self.obterEventosPrevistosDeputado(
            dep_id, data_final)
        if eventos_previstos:
            eventos_previstos = [x['id'] for x in eventos_previstos]
        else:
            eventos_previstos = []
        ausencia = 0
        for e in demais_eventos:
            if (e['id'] in eventos_previstos):
                ausencia += 1
                e['controleAusencia'] = 1
            elif (e['orgaos'][0]['nome'] in orgaos_dep or
                    e['orgaos'][0]['apelido'] == 'PLEN'):
                ausencia += 1
                e['controleAusencia'] = 2
            else:
                e['controleAusencia'] = None
        return demais_eventos, ausencia, eventos_previstos

    def obterProposicoesDeputado(self, deputado, data_final):
        di, df = self.obterDataInicialEFinal(data_final)
        try:
            for page in self.prop.obterTodasProposicoes(
                idDeputadoAutor=deputado.id,
                dataApresentacaoInicio=di,
                dataApresentacaoFim=df
            ):
                for item in page:
                    if (deputado.nome.lower() in 
                            [x['nome'].lower() for x in self.prop.obterAutoresProposicao(item['id'])]):
                        proposicao = Proposicao()
                        proposicao.id = str(item['id'])
                        p = self.prop.obterProposicao(item['id'])
                        if 'dataApresentacao' in p:
                            proposicao.data_apresentacao = p['dataApresentacao']
                        if 'ementa' in p:
                            proposicao.ementa = p['ementa']
                        if 'numero' in p:
                            proposicao.numero = str(p['numero'])
                        if 'siglaTipo' in p:
                            proposicao.tipo = p['siglaTipo']
                        if 'urlInteiroTeor' in p:
                            proposicao.url_documento = p['urlInteiroTeor']
                        self.relatorio.proposicoes.append(proposicao)
        except CamaraDeputadosError:
            self.relatorio.aviso_dados = 'Não foi possível obter proposições do parlamentar.'

    def obter_parlamentares(self):
        deputados = []
        for page in self.dep.obterTodosDeputados():
            for item in page:
                deputados.append(item)
        return deputados

    def obter_parlamentar(self, parlamentar_id):
        deputado_info = self.dep.obterDeputado(parlamentar_id)
        parlamentar = Parlamentar()
        parlamentar.cargo = 'BR1'
        parlamentar.id = str(deputado_info['id'])
        parlamentar.nome = deputado_info['ultimoStatus']['nome']
        parlamentar.partido = deputado_info['ultimoStatus']['siglaPartido']
        parlamentar.uf = deputado_info['ultimoStatus']['siglaUf']
        parlamentar.foto = deputado_info['ultimoStatus']['urlFoto']
        self.relatorio.parlamentar = parlamentar
        return parlamentar
