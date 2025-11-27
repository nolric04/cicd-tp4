"""
Exporteur Prometheus pour les métriques de tests
Expose les métriques via un endpoint HTTP que Prometheus peut scraper
"""

from prometheus_client import Counter, Gauge, Histogram, start_http_server
import time
import json
from pathlib import Path

# Métriques Prometheus
tests_total = Counter('tests_total', 'Total de tests exécutés', ['status', 'suite'])
tests_duration = Histogram('tests_duration_seconds', 'Durée des tests en secondes', ['suite'])
test_success_rate = Gauge('test_success_rate', 'Taux de succès des tests (0-100)', ['suite'])


class PrometheusExporter:
    """Exporte les métriques de tests vers Prometheus"""

    def __init__(self, port: int = 8000):
        self.port = port
        self.metrics_file = Path('reports')

    def start_server(self):
        """Démarre le serveur HTTP pour Prometheus"""
        start_http_server(self.port)
        print(f"✅ Serveur Prometheus démarré sur le port {self.port}")
        print(f"📍 Métriques disponibles: http://localhost:{self.port}/metrics")

    def update_metrics_from_allure(self):
        """Lit les résultats Allure et met à jour les métriques"""
        if not self.metrics_file.exists():
            print("⚠️  Aucun résultat Allure trouvé")
            return

        # Compter les tests par statut
        passed = 0
        failed = 0
        broken = 0
        skipped = 0

        # Parser les fichiers JSON Allure
        for result_file in self.metrics_file.glob('*-result.json'):
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)

                status = data.get('status', 'unknown')
                suite = 'default'  # On pourrait extraire depuis les labels
                duration = data.get('stop', 0) - data.get('start', 0)

                # Incrémenter les compteurs
                if status == 'passed':
                    passed += 1
                    tests_total.labels(status='passed', suite=suite).inc()
                elif status == 'failed':
                    failed += 1
                    tests_total.labels(status='failed', suite=suite).inc()
                elif status == 'broken':
                    broken += 1
                    tests_total.labels(status='broken', suite=suite).inc()
                elif status == 'skipped':
                    skipped += 1
                    tests_total.labels(status='skipped', suite=suite).inc()

                # Enregistrer la durée
                if duration > 0:
                    tests_duration.labels(suite=suite).observe(duration / 1000.0)  # ms -> s

            except Exception as e:
                print(f"⚠️  Erreur lecture {result_file}: {e}")

        # Calculer le taux de succès
        total = passed + failed + broken
        if total > 0:
            success_rate = (passed / total) * 100
            test_success_rate.labels(suite='all').set(success_rate)

        print(f"📊 Métriques mises à jour: {passed} passed, {failed} failed, {broken} broken, {skipped} skipped")


def main():
    """Point d'entrée principal"""
    exporter = PrometheusExporter(port=8000)
    exporter.start_server()

    # Mettre à jour les métriques toutes les 30 secondes
    while True:
        exporter.update_metrics_from_allure()
        time.sleep(30)


if __name__ == '__main__':
    main()