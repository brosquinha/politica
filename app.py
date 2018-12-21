# -*- coding: utf-8 -*-
import os
import json
from time import time
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import timedelta, datetime
from pytz import timezone
from db import MongoDBClient
from bson.objectid import ObjectId
from models.deputados import DeputadosApp
from models.deputadosSP import DeputadosALESPApp
from models.vereadoresSaoPaulo import VereadoresApp
from models.relatorio import Relatorio
from exceptions import ModelError
from send_reports import check_reports_to_send, send_email
from flask import Flask, request, render_template


app = Flask(__name__, static_url_path='/static')


def check_and_send_reports():
    return send_reports(check_reports_to_send())


def send_reports(data):
    dep = DeputadosApp()
    for item in data:
        reports = []
        for par in item["parlamentares"]:
            reports.append(obter_relatorio(
                par,
                datetime.now().strftime('%Y-%m-%d'),
                dep.consultar_deputado,
                deputado_id=par,
                data_final=datetime.now().strftime('%Y-%m-%d'),
                periodo_dias=item["intervalo"]
            ))
        with app.app_context():
            html_report = render_template(
                'relatorio_deputado_email.out.html',
                relatorios=reports,
                data_final=datetime.now().strftime('%Y-%m-%d'),
                intervalo=item["intervalo"]
            )
        send_email(item["email"], html_report)


scheduler = BackgroundScheduler()
scheduler.configure(timezone=timezone('America/Sao_Paulo'))
scheduler.add_job(
    func=check_and_send_reports,
    trigger='cron',
    day_of_week='sat',
    hour='12',
    minute='0',
    second=0,
    day='*',
    month='*'
)


@app.route('/')
def home():
    return render_template('consultar_form.html'), 200


def modelar_pagina_relatorio(relatorio, template='consulta_deputado.html'):
    return render_template(
        template,
        relatorio=relatorio
    ), 200


def obter_relatorio(parlamentar, data, func, **kwargs):
    """
    Obtém o relatório da função fornecida

    Espera-se que `func` retorne um objeto Relatorio.
    """
    mongo_db = MongoDBClient()
    relatorios_col = mongo_db.get_collection('relatorios')
    relatorio = relatorios_col.find_one({'idTemp': '{}-{}'.format(parlamentar, data)})
    if relatorio != None:
        print('Relatorio carregado!')
        relatorio['_id'] = str(relatorio['_id'])
        return relatorio
    else:
        try:
            relatorio = func(**kwargs)
            relatorio_dict = relatorio.to_dict()
            relatorio_dict['_id'] = str(relatorios_col.insert_one(
                {
                    **relatorio_dict,
                    **{'idTemp': '{}-{}'.format(parlamentar, data)}
                }
            ).inserted_id)
            return relatorio_dict
        except ModelError as e:
            return render_template(
                'erro.html',
                erro_titulo='500 - Serviço indisponível',
                erro_descricao=e.message
            ), 500


@app.route('/relatorio')
def consultar_parlamentar():
    if request.args.get('parlamentarTipo') == 'deputados':
        dep = DeputadosApp()
        if 'data' not in request.args:
            data_final = datetime.now().strftime('%Y-%m-%d')
        else:
            data_final = request.args.get('data')
        return modelar_pagina_relatorio(obter_relatorio(
            parlamentar=request.args.get('parlamentar'),
            data=data_final,
            func=dep.consultar_deputado,
            deputado_id=request.args.get('parlamentar'),
            data_final=data_final,
            periodo_dias=request.args.get('dias')
        ))
    elif request.args.get('parlamentarTipo') == 'vereadores':
        ver = VereadoresApp()
        return modelar_pagina_relatorio(obter_relatorio(
            parlamentar=request.args.get('parlamentar'),
            data=request.args.get('data'),
            func=ver.consultar_vereador,
            vereador_nome=request.args.get('parlamentar'),
            data_final=request.args.get('data'),
            periodo=request.args.get('dias')
        ))
    elif request.args.get('parlamentarTipo') == 'deputadosSP':
        depsp = DeputadosALESPApp()
        return modelar_pagina_relatorio(obter_relatorio(
            parlamentar=request.args.get('parlamentar'),
            data=request.args.get('data'),
            func=depsp.consultar_deputado,
            dep_id=request.args.get('parlamentar'),
            data_final=request.args.get('data'),
            periodo=7
        ))
    else:
        return 'Selecione um tipo de parlamentar, plz', 400


@app.route('/avaliar', methods=['POST'])
def avaliar():
    #POC: melhorar modelagem disso, plz
    relatorio = request.form.get('id')
    avaliacao_valor = request.form.get('avaliacao')
    avaliado = request.form.get('avaliado')
    email = os.environ.get("GMAIL_USR")
    avaliacao = {}
    mongo_client = MongoDBClient()
    avaliacoes_col = mongo_client.get_collection('avaliacoes')
    relatorios_col = mongo_client.get_collection('relatorios')
    relatorio = relatorios_col.find_one({'_id': ObjectId(relatorio)})
    for tipo in ['eventosAusentes', 'eventosPresentes', 'proposicoes']:
        for item in relatorio[tipo]:
            if 'id' in item and str(item['id']) == avaliado:
                avaliacao['avaliado'] = item
                break
    if not 'avaliado' in avaliacao:
        return 'Item not found', 400
    avaliacao['parlamentar'] = relatorio['parlamentar']
    avaliacao['email'] = email
    avaliacao['relatorioId'] = relatorio['_id']
    avaliacao['avaliacao'] = avaliacao_valor
    avaliacao_existente = avaliacoes_col.find_one({
        'avaliado.id': avaliacao['avaliado']['id'],
        'parlamentar.id': relatorio['parlamentar']['id'],
        'parlamentar.cargo': relatorio['parlamentar']['cargo'],
        'email': email,
        'relatorioId': relatorio['_id']
    })
    if avaliacao_existente:
        avaliacoes_col.update_one(
            {'_id': avaliacao_existente['_id']}, {'$set': {'avaliacao': avaliacao_valor}})
    else:
        avaliacoes_col.insert_one(avaliacao)
    mongo_client.close()
    return 'Created', 201


@app.route('/API/minhasAvaliacoes')
def avaliacoes():
    #POC
    try:
        cargo = request.args['parlamentarTipo']
        parlamentar = request.args['parlamentar']
    except KeyError:
        return json.dumps({'error': 'Missing arguments'}), 400
    mongo_client = MongoDBClient()
    avaliacoes_col = mongo_client.get_collection('avaliacoes')
    avaliacoes = [i for i in avaliacoes_col.find(
        {
            'parlamentar.id': parlamentar,
            'parlamentar.cargo': cargo,
            'email': os.environ.get('GMAIL_USR')
        }
    )]
    mongo_client.close()
    return json.dumps(avaliacoes, default=str), 200


@app.route('/API/relatorioDeputado')
def consultar_deputado_api():
    dep = DeputadosApp()
    return json.dumps(obter_relatorio(
        parlamentar=request.args.get('parlamentar'),
        data=request.args.get('data'),
        func=dep.consultar_deputado,
        deputado_id=request.args.get('parlamentar'),
        data_final=request.args.get('data'),
        periodo_dias=request.args.get('dias')
    ), default=str), 200


@app.route('/deputados')
def obterDeputados():
    dep = DeputadosApp()
    return dep.obterDeputados()


@app.route('/deputadosSP')
def obterDeputadosAlesp():
    dep = DeputadosALESPApp()
    return dep.obterDeputados()


@app.route('/vereadores')
def obterVereadores():
    ver = VereadoresApp()
    return ver.obterVereadoresAtuais()


@app.errorhandler(500)
def server_error(e):
    return render_template(
        'erro.html',
        erro_titulo="500 - Erro interno do servidor",
        erro_descricao="Yep... cometemos um erro, precisamos corrigir. Sorry."
    ), 500


@app.errorhandler(404)
def not_found(e):
    return render_template(
        'erro.html',
        erro_titulo="404 - Página não encontrada",
        erro_descricao="O clássico. Definitivamente esse recurso não existe."
    ), 404


@app.errorhandler(400)
def client_error(e):
    return render_template(
        'erro.html',
        erro_titulo="404 - Erro do cliente",
        erro_descricao="Aeow, tu não estás fazendo a requisição do jeito certo."
    ), 400


if __name__ == '__main__':
    app.debug = os.environ.get('DEBUG', 'True') in ['True', 'true']
    port = int(os.environ.get('PORT', 5000))
    scheduler.start()
    app.run(host='0.0.0.0', port=port, threaded=True)
