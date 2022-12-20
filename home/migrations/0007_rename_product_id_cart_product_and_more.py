# Generated by Django 4.1.4 on 2022-12-20 06:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0006_alter_products_image'),
    ]

    operations = [
        migrations.RenameField(
            model_name='cart',
            old_name='product_id',
            new_name='product',
        ),
        migrations.RenameField(
            model_name='cart',
            old_name='user_id',
            new_name='user',
        ),
        migrations.RenameField(
            model_name='cities',
            old_name='province_id',
            new_name='province',
        ),
        migrations.RenameField(
            model_name='payment',
            old_name='order_id',
            new_name='order',
        ),
        migrations.RenameField(
            model_name='productpurchases',
            old_name='product_id',
            new_name='product',
        ),
        migrations.RenameField(
            model_name='productpurchases',
            old_name='user_id',
            new_name='user',
        ),
        migrations.RenameField(
            model_name='products',
            old_name='brand_id',
            new_name='brand',
        ),
        migrations.RenameField(
            model_name='products',
            old_name='category_id',
            new_name='category',
        ),
        migrations.RenameField(
            model_name='products',
            old_name='size_id',
            new_name='size',
        ),
        migrations.RenameField(
            model_name='shipment',
            old_name='city_id',
            new_name='city',
        ),
        migrations.RenameField(
            model_name='shipment',
            old_name='user_id',
            new_name='user',
        ),
        migrations.RenameField(
            model_name='sizes',
            old_name='size_category_id',
            new_name='size_category',
        ),
        migrations.AlterField(
            model_name='products',
            name='image',
            field=models.ImageField(null=True, upload_to='home/image_upload'),
        ),
    ]