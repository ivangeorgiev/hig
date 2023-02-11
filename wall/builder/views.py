from rest_framework.views import APIView
from rest_framework.response import Response

from .builder import History


class ProfileIceAmountPerDay(APIView):
    def get(self, request, profile, day):
        return Response({"day": day, "ice_amount": History.amount_per_profile_per_day(profile, day)})


class ProfilePricePerDay(APIView):
    def get(self, request, profile, day):
        return Response({"day": day, "cost": History.price_per_profile_per_day(profile, day)})


class PricePerDay(APIView):
    def get(self, request, day):
        return Response({"day": day, "cost": History.price_per_day(day)})


class PriceTotal(APIView):
    def get(self, request):
        return Response({"day": None, "cost": History.overall()})
