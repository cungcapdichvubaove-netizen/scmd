# Generated for SCMD Pro guard patrol domain correction Phase 2.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0018_guard_patrol_operations_schedule'),
        ('inspection', '0008_guard_patrol_shift_compliance'),
    ]

    operations = [
        migrations.AddField(
            model_name='luottuantra',
            name='lich_tuan_tra_van_hanh',
            field=models.ForeignKey(blank=True, help_text='Phase 2: truy vết lượt tuần tra về lịch tuần tra do operations tạo.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='luot_tuan_tra_bao_ve', to='operations.lichtuantravanhanh', verbose_name='Lịch tuần tra vận hành'),
        ),
        migrations.AddField(
            model_name='luottuantra',
            name='nhiem_vu_tuan_tra_ca',
            field=models.ForeignKey(blank=True, help_text='Phase 2: truy vết lượt tuần tra về nhiệm vụ cụ thể trong ca trực.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='luot_tuan_tra_bao_ve', to='operations.nhiemvutuantraca', verbose_name='Nhiệm vụ tuần tra theo ca'),
        ),
    ]
