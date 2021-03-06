import unittest

from tests.integration.test_alesp import TestALESPHandlerIntegration
from tests.integration.test_app import TestApp
from tests.integration.test_assemblyman_controller import \
    TestAssemblymanController
from tests.integration.test_camara_deputados import \
    TestCamaraDeputadosHandlerIntegration
from tests.integration.test_camara_municipal_sao_paulo import \
    TestCamaraMunicipalSaoPauloHandlerIntegration
from tests.integration.test_device_controller import TestDeviceController
from tests.integration.test_house_controller import TestHouseController
from tests.integration.test_report_controller import TestReportController
from tests.integration.test_subscription_controller import \
    TestSubscriptionController
from tests.integration.test_user_controller import TestUserController
from tests.unit.test_alesp import TestALESPHandler
from tests.unit.test_avaliacoes import TestAvaliacao
from tests.unit.test_camara_deputados import TestCamaraDeputadosHandler
from tests.unit.test_camara_deputados_helper import TestCamaraDeputadosHelper
from tests.unit.test_camara_municipal_sao_paulo import \
    TestCamaraMunicipalSaoPauloHandler
from tests.unit.test_casa_legislativa import TestCasaLegislativa
from tests.unit.test_cron import TestCron
from tests.unit.test_dispositivos import TestDispositivos
from tests.unit.test_dto import TestDTOs
from tests.unit.test_inscricoes import TestInscricao
from tests.unit.test_relatorios import TestRelatorios
from tests.unit.test_send_reports import TestSendReports
from tests.unit.test_usuarios import TestUsuario

if __name__ == '__main__':
    unittest.main(verbosity=1)
