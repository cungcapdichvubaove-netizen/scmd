# Generated for SCMD Pro guard patrol domain correction Phase 2.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('clients', '0012_customer_payment_phase_e'),
        ('inspection', '0008_guard_patrol_shift_compliance'),
        ('operations', '0017_shift_change_request_applied_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='LichTuanTraVanHanh',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tenant_id', models.UUIDField(db_index=True, default='00000000-0000-0000-0000-000000000001', editable=False, help_text='Organization scope identifier. Legacy name: tenant_id. SCMD Pro hiện là single-organization hardened deployment.')),
                ('tan_suat_luot_bat_buoc', models.PositiveSmallIntegerField(default=1, help_text='Số nhiệm vụ tuần tra cần tạo cho mỗi phân công ca phù hợp.', verbose_name='Số lượt bắt buộc trong ca')),
                ('khung_gio_bat_dau', models.TimeField(blank=True, null=True, verbose_name='Khung giờ bắt đầu')),
                ('khung_gio_ket_thuc', models.TimeField(blank=True, null=True, verbose_name='Khung giờ kết thúc')),
                ('grace_minutes', models.PositiveSmallIntegerField(default=10, verbose_name='Grace minutes')),
                ('yeu_cau_gps', models.BooleanField(default=False, verbose_name='Bắt buộc GPS')),
                ('yeu_cau_anh', models.BooleanField(default=False, verbose_name='Bắt buộc ảnh')),
                ('trang_thai', models.CharField(choices=[('ACTIVE', 'Đang áp dụng'), ('INACTIVE', 'Tạm ngưng')], db_index=True, default='ACTIVE', max_length=16, verbose_name='Trạng thái')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Tạo lúc')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Cập nhật lúc')),
                ('ca_lam_viec', models.ForeignKey(blank=True, help_text='Để trống nếu lịch áp dụng cho mọi ca tại mục tiêu/chốt.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='lich_tuan_tra_van_hanh', to='operations.calamviec', verbose_name='Ca trực áp dụng')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lich_tuan_tra_van_hanh_da_tao', to=settings.AUTH_USER_MODEL, verbose_name='Người tạo')),
                ('muc_tieu', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='lich_tuan_tra_van_hanh', to='clients.muctieu', verbose_name='Mục tiêu bảo vệ')),
                ('tuyen_tuan_tra', models.ForeignKey(help_text='Bảng tuyến hiện còn legacy trong inspection; owner nghiệp vụ là operations.', on_delete=django.db.models.deletion.PROTECT, related_name='lich_van_hanh', to='inspection.loaituantra', verbose_name='Tuyến tuần tra vận hành')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lich_tuan_tra_van_hanh_da_cap_nhat', to=settings.AUTH_USER_MODEL, verbose_name='Người cập nhật')),
                ('vi_tri_chot', models.ForeignKey(blank=True, help_text='Để trống nếu lịch áp dụng cho mọi chốt thuộc mục tiêu.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='lich_tuan_tra_van_hanh', to='operations.vitrichot', verbose_name='Vị trí chốt áp dụng')),
            ],
            options={
                'verbose_name': 'Lịch tuần tra theo ca',
                'verbose_name_plural': 'Lịch tuần tra theo ca',
                'ordering': ['muc_tieu__ten_muc_tieu', 'vi_tri_chot__ten_vi_tri', 'ca_lam_viec__gio_bat_dau', 'tuyen_tuan_tra__ten_loai'],
                'permissions': [('quan_ly_lich_tuan_tra_van_hanh', 'Có thể quản lý lịch tuần tra vận hành'), ('xem_doi_soat_tuan_tra_van_hanh', 'Có thể xem đối soát tuần tra vận hành')],
            },
        ),
        migrations.CreateModel(
            name='NhiemVuTuanTraCa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tenant_id', models.UUIDField(db_index=True, default='00000000-0000-0000-0000-000000000001', editable=False, help_text='Organization scope identifier. Legacy name: tenant_id. SCMD Pro hiện là single-organization hardened deployment.')),
                ('thu_tu_luot', models.PositiveSmallIntegerField(default=1, verbose_name='Thứ tự lượt trong ca')),
                ('thoi_gian_bat_dau_du_kien', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='Bắt đầu dự kiến')),
                ('thoi_gian_ket_thuc_du_kien', models.DateTimeField(blank=True, null=True, verbose_name='Kết thúc dự kiến')),
                ('grace_deadline', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='Hạn grace')),
                ('trang_thai', models.CharField(choices=[('PLANNED', 'Đã lên lịch'), ('IN_PROGRESS', 'Đang thực hiện'), ('COMPLETED_VALID', 'Hoàn thành hợp lệ'), ('COMPLETED_WITH_WARNINGS', 'Hoàn thành có cảnh báo'), ('MISSED', 'Bỏ lượt/thiếu điểm'), ('CANCELLED_WITH_REASON', 'Đã hủy có lý do')], db_index=True, default='PLANNED', max_length=32, verbose_name='Trạng thái nhiệm vụ')),
                ('so_diem_bat_buoc', models.PositiveIntegerField(default=0, verbose_name='Số điểm bắt buộc')),
                ('so_diem_da_quet', models.PositiveIntegerField(default=0, verbose_name='Số điểm đã quét')),
                ('so_diem_canh_bao', models.PositiveIntegerField(default=0, verbose_name='Số điểm có cảnh báo')),
                ('ly_do_huy_bo', models.TextField(blank=True, verbose_name='Lý do hủy/bỏ lượt')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Tạo lúc')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Cập nhật lúc')),
                ('lich_tuan_tra', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='nhiem_vu_theo_ca', to='operations.lichtuantravanhanh', verbose_name='Lịch tuần tra vận hành')),
                ('luot_tuan_tra', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='nhiem_vu_van_hanh', to='inspection.luottuantra', verbose_name='Lượt tuần tra thực tế')),
                ('phan_cong_ca_truc', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='nhiem_vu_tuan_tra', to='operations.phancongcatruc', verbose_name='Phân công ca trực')),
                ('tuyen_tuan_tra', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='nhiem_vu_van_hanh', to='inspection.loaituantra', verbose_name='Tuyến tuần tra')),
            ],
            options={
                'verbose_name': 'Nhiệm vụ tuần tra theo ca',
                'verbose_name_plural': 'Nhiệm vụ tuần tra theo ca',
                'ordering': ['phan_cong_ca_truc__ngay_truc', 'phan_cong_ca_truc__ca_lam_viec__gio_bat_dau', 'thu_tu_luot'],
                'permissions': [('thuc_hien_tuan_tra_bao_ve', 'Có thể thực hiện tuần tra bảo vệ'), ('xu_ly_canh_bao_tuan_tra_van_hanh', 'Có thể xử lý cảnh báo tuần tra vận hành')],
            },
        ),
        migrations.AddIndex(
            model_name='lichtuantravanhanh',
            index=models.Index(fields=['tenant_id', 'trang_thai', 'muc_tieu'], name='ops_gpsched_tenant_mt_idx'),
        ),
        migrations.AddIndex(
            model_name='lichtuantravanhanh',
            index=models.Index(fields=['tenant_id', 'vi_tri_chot', 'ca_lam_viec'], name='ops_gpsched_post_shift_idx'),
        ),
        migrations.AddIndex(
            model_name='nhiemvutuantraca',
            index=models.Index(fields=['tenant_id', 'trang_thai', 'thoi_gian_bat_dau_du_kien'], name='ops_gptask_tenant_stat_idx'),
        ),
        migrations.AddIndex(
            model_name='nhiemvutuantraca',
            index=models.Index(fields=['tenant_id', 'phan_cong_ca_truc', 'trang_thai'], name='ops_gptask_shift_stat_idx'),
        ),
        migrations.AddIndex(
            model_name='nhiemvutuantraca',
            index=models.Index(fields=['tenant_id', 'grace_deadline'], name='ops_gptask_grace_idx'),
        ),
        migrations.AddConstraint(
            model_name='lichtuantravanhanh',
            constraint=models.CheckConstraint(check=models.Q(('tan_suat_luot_bat_buoc__gte', 1)), name='ck_guard_patrol_schedule_freq_ge_1'),
        ),
        migrations.AddConstraint(
            model_name='nhiemvutuantraca',
            constraint=models.UniqueConstraint(fields=('tenant_id', 'lich_tuan_tra', 'phan_cong_ca_truc', 'thu_tu_luot'), name='uq_guard_patrol_task_per_shift'),
        ),
        migrations.AddConstraint(
            model_name='nhiemvutuantraca',
            constraint=models.CheckConstraint(check=models.Q(('thu_tu_luot__gte', 1)), name='ck_guard_patrol_task_order_ge_1'),
        ),
    ]
