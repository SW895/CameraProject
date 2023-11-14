from django import forms

class Video_created_date(forms.Form):
    date = forms.DateField(widget=forms.SelectDateWidget(empty_label=("Choose Year", "Choose Month", "Choose Day")))
    #objects = forms.BooleanField(widget=forms.CheckboxInput, label="")