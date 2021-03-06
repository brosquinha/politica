from flask import request
from flask_login import login_required
from flask_restplus import Resource, abort, fields

from legislei.app import current_user, rest_api_v1
from legislei.controllers.dto import devices_dto
from legislei.exceptions import DispositivosModuleError
from legislei.services.dispositivos import Dispositivo

_patch_devices_dto = rest_api_v1.model("Device", {
    'token': fields.String(description="Token de envio de notificações", required=False),
    'active': fields.Boolean(description="Se o Legislei deve enviar notificações para esse dispositivo ou não", required=False),
    'name': fields.String(description="Nome do dispositivo", required=False),
    'os': fields.String(description="Sistema operacional do dispositivo", required=False)
})

@rest_api_v1.route("/usuarios/dispositivos")
class DeviceList(Resource):
    @login_required
    @rest_api_v1.doc(
        description="Retorna todos os dispositivos do usuário de id informado",
        security='apikey',
        responses={
            200: 'Sucesso',
            401: 'Sem autenticação',
            403: 'Usuário logado sem permissão para acessar dispositivos de outros usuários'
        }
    )
    @rest_api_v1.marshal_list_with(devices_dto)
    def get(self):
        return Dispositivo().obter_dispositivos_de_usuario(str(current_user.id))

    @login_required
    @rest_api_v1.doc(
        description="Insere um novo dispositivo do usuário",
        security='apikey',
        responses={
            201: 'Sucesso',
            400: 'Parâmetros inválidos ou incompletos',
            401: 'Sem autenticação',
            422: 'Parâmetros inválidos'
        }
    )
    @rest_api_v1.expect(devices_dto, validate=True)
    def post(self):
        try:
            Dispositivo().adicionar_dispostivo(
                str(current_user.id),
                request.json["uuid"],
                request.json["token"],
                request.json["name"],
                active=True,
                os=request.json.get("os")
            )
            return {'message': 'Criado'}, 201
        except DispositivosModuleError as e:
            abort(422, message=e.message)


@rest_api_v1.route("/usuarios/dispositivos/<dispositivo_uuid>")
class Device(Resource):
    @login_required
    @rest_api_v1.doc(
        description="Atualiza alguns parâmetros de um dispositivo do usuário informado",
        security='apikey',
        responses={
            200: 'sucesso',
            400: 'Parâmetros inválidos ou incompletos',
            401: 'Sem autenticação',
        }
    )
    @rest_api_v1.expect(_patch_devices_dto, validate=True)
    def patch(self, dispositivo_uuid):
        try:
            Dispositivo().atualizar_dispositivo(
                str(current_user.id), dispositivo_uuid, **request.json
            )
            return {'message': 'Ok'}, 200
        except DispositivosModuleError as e:
            abort(400, message=e.message)

    @login_required
    @rest_api_v1.doc(
        description="Apaga dispositivo da lista do usuário fornecido",
        security='apikey',
        responses={
            200: 'Sucesso',
            401: 'Sem autenticação',
            403: 'Usuário logado sem permissão para acessar dispositivos de outros usuários'
        }
    )
    def delete(self, dispositivo_uuid):
        Dispositivo().apagar_dispositivo(str(current_user.id), dispositivo_uuid)
        return {'message': 'Apagado'}, 200
