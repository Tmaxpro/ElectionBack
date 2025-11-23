import requests
import json
from typing import List, Dict, Optional
from datetime import datetime

class ACIMSMSClient:
    """Client pour l'API SMS PRO d'ACIM SARL"""
    
    def __init__(self, username: str, token: str, sender: str):
        """
        Initialise le client SMS
        
        Args:
            username: Nom d'utilisateur du compte SMS
            token: Token du compte SMS
        """
        self.base_url = "https://sms.acim-ci.net:8443/api"
        self.username = username
        self.token = token
        self.sender = sender
        self.sent_messages = []  # Messages envoyés avec succès
        self.failed_messages = []  # Messages échoués
        
    def send_one_sms(self, dest: str, message: str, 
                     flash: str = "", titre: str = "") -> Dict:
        """
        Envoie un SMS à un seul destinataire
        
        Args:
            dest: Numéro du destinataire (ex: 2250554760285)
            message: Contenu du SMS
            sender: Nom de l'expéditeur (11 caractères max)
            flash: Paramètre pour affichage direct
            titre: Nom de la campagne
            
        Returns:
            Dict contenant la réponse et le statut
        """
        url = f"{self.base_url}/addOneSms"
        
        payload = {
            "Username": self.username,
            "Token": self.token,
            "Dest": dest,
            "Sms": message,
            "Sender": self.sender,
            "Flash": flash,
            "Titre": titre
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            # Analyse du statut
            status_info = self._analyze_send_status(result, dest, message)
            
            # Stockage selon le statut
            if status_info['success']:
                self.sent_messages.append(status_info)
            else:
                self.failed_messages.append(status_info)
            
            return status_info
            
        except requests.exceptions.RequestException as e:
            error_info = {
                'success': False,
                'error': str(e),
                'dest': dest,
                'message': message,
                'timestamp': datetime.now().isoformat()
            }
            self.failed_messages.append(error_info)
            return error_info
    
    def send_bulk_sms(self, messages: List[Dict]) -> Dict:
        """
        Envoie plusieurs SMS de contenus différents à plusieurs destinataires
        
        Args:
            messages: Liste de dicts avec clés 'Dest', 'Sms', 'Sender', 'Flash'
                     Exemple: [
                         {"Dest": "225055...", "Sms": "Message 1", "Sender": "ACIM", "Flash": ""},
                         {"Dest": "225055...", "Sms": "Message 2", "Sender": "ACIM", "Flash": ""}
                     ]
        
        Returns:
            Dict contenant la réponse et le statut détaillé
        """
        url = f"{self.base_url}/addBulkSms"
        
        payload = {
            "Username": self.username,
            "Token": self.token,
            "Mssg": messages
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            # Analyse du statut
            status_info = self._analyze_send_status(result, "bulk", f"{len(messages)} messages")
            status_info['messages_count'] = len(messages)
            status_info['messages_details'] = messages
            
            # Stockage selon le statut
            if status_info['success']:
                self.sent_messages.append(status_info)
            else:
                self.failed_messages.append(status_info)
            
            return status_info
            
        except requests.exceptions.RequestException as e:
            error_info = {
                'success': False,
                'error': str(e),
                'messages_count': len(messages),
                'timestamp': datetime.now().isoformat()
            }
            self.failed_messages.append(error_info)
            return error_info
    
    def get_delivery_report(self, ref: str, dest: str) -> Dict:
        """
        Récupère l'accusé de réception d'un SMS
        
        Args:
            ref: Référence du SMS
            dest: Numéro du destinataire
            
        Returns:
            Dict contenant l'accusé de réception et son analyse
        """
        url = f"{self.base_url}/getAccuses"
        
        payload = {
            "Username": self.username,
            "Ref": ref,
            "Dest": dest
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            # Analyse de l'accusé de réception
            delivery_info = self._analyze_delivery_status(result)
            
            return delivery_info
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'ref': ref,
                'dest': dest,
                'timestamp': datetime.now().isoformat()
            }
    
    def _analyze_send_status(self, response: Dict, dest: str, message: str) -> Dict:
        """Analyse la réponse d'envoi et détermine le statut"""
        status_info = {
            'timestamp': datetime.now().isoformat(),
            'dest': dest,
            'message': message,
            'raw_response': response
        }
        
        # Vérification de l'état (Etat)
        etat = response.get('Etat', -1)
        
        if etat == 1:
            status_info['success'] = True
            status_info['status'] = 'SMS envoyé avec succès'
            
            # Extraction des informations supplémentaires
            if 'Rep' in response and len(response['Rep']) > 0:
                rep = response['Rep'][0]
                status_info['ref'] = rep.get('Ref', '')
                status_info['sender'] = rep.get('Sender', '')
                status_info['sms_count'] = rep.get('Cpt_sms', 1)
                status_info['statut_detail'] = rep.get('Statut', '')
                
        elif etat == 0:
            status_info['success'] = False
            status_info['status'] = 'Échec - Exécution échouée'
            status_info['error_detail'] = response.get('Rep', [{}])[0].get('Statut', 'Erreur inconnue')
            
        elif etat == 2:
            status_info['success'] = False
            status_info['status'] = 'Échec - Username ou Token incorrect'
            
        else:
            status_info['success'] = False
            status_info['status'] = 'Échec - État inconnu'
        
        return status_info
    
    def _analyze_delivery_status(self, response: Dict) -> Dict:
        """Analyse l'accusé de réception"""
        delivery_info = {
            'timestamp': datetime.now().isoformat(),
            'raw_response': response
        }
        
        if 'Accs' in response and len(response['Accs']) > 0:
            acc = response['Accs'][0].get('Acc', {})
            
            delivery_info['ref'] = acc.get('Ref', '')
            delivery_info['dest'] = acc.get('Dest', '')
            delivery_info['sender'] = acc.get('Sender', '')
            
            # Analyse du StatutSmc
            statut_smc = acc.get('Statutsmc', '')
            delivery_info['statut_smc'] = statut_smc
            delivery_info['smc_description'] = self._get_smc_description(statut_smc)
            
            # Analyse du StatutDelivred
            statut_delivred = acc.get('Statutdelivred', '')
            delivery_info['statut_delivred'] = statut_delivred
            delivery_info['delivery_description'] = self._get_delivery_description(statut_delivred)
            
            # Détermination du succès
            delivery_info['delivered'] = (statut_delivred == 'delivered')
            delivery_info['success'] = (acc.get('Statut', 0) == 1)
            
            # Dates
            delivery_info['date_insertion'] = acc.get('Dateinsertion', '')
            delivery_info['date_send'] = acc.get('Datesend', '')
            delivery_info['date_accused'] = acc.get('Dateaccused', '')
            
        else:
            delivery_info['success'] = False
            delivery_info['error'] = 'Aucun accusé de réception trouvé'
        
        return delivery_info
    
    def _get_smc_description(self, statut_smc: str) -> str:
        """Retourne la description du statut SMC"""
        descriptions = {
            'ESME_ROK': 'Envoyé au Serveur SMSC',
            'ESME_RINVDSTADR': 'Destinataire incorrect',
            'ESME_RINVSRCADR': 'Sender incorrect',
            'ESME_RINVMSGLEN': 'Message trop long',
            'SENDER_NOT_RECORD': 'Sender non enregistré',
            'INACTIVE_ACCOUNT': 'Compte SMS désactivé',
            'NO_CREDIT': 'Pas de crédit SMS',
            'EXPIRED': "Délai d'envoi du SMS expiré"
        }
        return descriptions.get(statut_smc, 'Statut inconnu')
    
    def _get_delivery_description(self, statut_delivred: str) -> str:
        """Retourne la description du statut de livraison"""
        descriptions = {
            'delivered': 'SMS délivré au destinataire',
            'pending': "SMS en attente d'être délivré",
            'expired': "Délai d'attente expiré",
            'undelivered': 'SMS non délivré au destinataire',
            'failed': "Envoi du SMS échoué"
        }
        return descriptions.get(statut_delivred, 'Statut inconnu')
    
    def get_sent_summary(self) -> Dict:
        """Retourne un résumé des messages envoyés"""
        return {
            'total_sent': len(self.sent_messages),
            'total_failed': len(self.failed_messages),
            'sent_messages': self.sent_messages,
            'failed_messages': self.failed_messages
        }
    
    def reset_history(self):
        """Réinitialise l'historique des envois"""
        self.sent_messages = []
        self.failed_messages = []
