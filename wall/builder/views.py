from rest_framework.views import APIView
from rest_framework.response import Response

from builder import History


class ProfileIceAmountPerDay(APIView):
    def get(self, request):
        pass


class ProfilePricePerDay(APIView):
    def get(self, request):
        pass


class PricePerDay(APIView):
    def get(self, request):
        pass


class PriceTotal(APIView):
    def get(self, request):
        # History.overall()
        pass

