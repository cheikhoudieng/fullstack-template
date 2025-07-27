
import logging
from django.db.models import Prefetch
from django.http import Http404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import  NotFound

from orders.models import Order, OrderItem, OrderShopShipment
from orders.serializers import (
    UserOrderListSerializer,
    UserOrderDetailSerializer,
)

logger = logging.getLogger(__name__)

class UserOrderListView(generics.ListAPIView):
    """
    Vue API pour lister TOUTES les commandes passées
    par l'utilisateur authentifié.
    """
    serializer_class = UserOrderListSerializer
    permission_classes = [permissions.IsAuthenticated] # Seul l'utilisateur connecté

    def get_queryset(self):
        """
        Retourne uniquement les commandes de l'utilisateur connecté.
        """
        user = self.request.user
        logger.info(f"Fetching order list for user: {user.id}")

        queryset = Order.objects.filter(user=user)

        # Optimisation simple pour la liste : précharger count() si nécessaire,
        # sinon juste ordonner par date.
        # Si get_item_count utilise order.order_items.count(), il FAUT précharger :
        queryset = queryset.prefetch_related('order_items') # Pour get_item_count

        queryset = queryset.order_by('-added_date') # Le plus récent en premier
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        logger.debug(f"User {request.user.id} listing {queryset.count()} orders.")
        return super().list(request, *args, **kwargs)


class UserOrderDetailView(generics.RetrieveAPIView):
    """
    Vue API pour afficher les détails complets d'une commande spécifique
    appartenant à l'utilisateur authentifié.
    """
    serializer_class = UserOrderDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'          # Recherche par ID (UUID) de la commande
    lookup_url_kwarg = 'order_id' # Nom du paramètre dans l'URL

    def get_queryset(self):
        """
        Retourne un queryset de base contenant SEULEMENT les commandes
        de l'utilisateur connecté. La sécurité est gérée ici avant
        que RetrieveAPIView ne cherche l'ID spécifique.
        """
        user = self.request.user
        # Très important : filtrer par utilisateur ici !
        queryset = Order.objects.filter(user=user)

        # Pré-charger TOUTES les données nécessaires pour UserOrderDetailSerializer
        queryset = queryset.select_related(
            'user',             # Déjà filtré mais bon pour le serializer
            'delivery_location',
            # 'payment',        # Si le serializer inclut des infos de paiement
        ).prefetch_related(
            # Items avec produit et sa boutique
            Prefetch('order_items', queryset=OrderItem.objects.select_related('product__shop')),
            # Shipments avec boutique et méthode
            Prefetch('shop_shipments', queryset=OrderShopShipment.objects.select_related('shop', 'delivery_method')),
        )
        return queryset

    def retrieve(self, request, *args, **kwargs):
        """Gère la récupération et la sérialisation de l'objet."""
        # get_object() utilise get_queryset(), donc la sécurité est déjà appliquée.
        # Si l'order_id existe mais n'appartient pas à l'utilisateur,
        # il ne sera pas trouvé dans le queryset => Http404.
        try:
            instance = self.get_object()
            logger.info(f"User {request.user.id} accessing detail for order {instance.id}")
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Http404:
            # Log spécifique pour le cas où l'ordre n'est pas trouvé POUR CET UTILISATEUR
            logger.warning(f"User {request.user.id} tried to access order {kwargs.get('order_id')} which was not found or not theirs.")
            raise NotFound(detail="Order not found or you do not have permission to view it.")
             # Vous pouvez personnaliser le message si vous préférez ne pas révéler l'existence de l'ID
             # raise NotFound(detail="Order not found.")
        except Exception as e:
            logger.error(f"Error retrieving order detail for user {request.user.id}, order {kwargs.get('order_id')}: {e}", exc_info=True)
            return Response({"error": "An unexpected error occurred while retrieving the order."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)