# encoding: utf-8
from django import forms
from django.utils.translation import ugettext_lazy as _

from seahub.profile.models import Profile, DetailedProfile

class ProfileForm(forms.Form):
    nickname = forms.CharField(max_length=64, required=False)
    intro = forms.CharField(max_length=256, required=False)

    def save(self, username):
        nickname = self.cleaned_data['nickname']
        intro = self.cleaned_data['intro']
        Profile.objects.add_or_update(username, nickname, intro)
        
        
class DetailedProfileForm(ProfileForm):
    department = forms.CharField(max_length=512)
    telephone = forms.CharField(max_length=100)

    def save(self, username):
        super(DetailedProfileForm, self).save(username)
        department = self.cleaned_data['department']
        telephone = self.cleaned_data['telephone']
        DetailedProfile.objects.add_or_update(username, department, telephone)
        
