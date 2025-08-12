import csv
import os
import requests
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from django.conf import settings
from store.models import (
    Product,
)  # Replace 'yourapp' with your actual app name


class Command(BaseCommand):
    help = "Seed the database with products from WooCommerce CSV"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-path",
            type=str,
            help="Path to the CSV file",
            default="Divi-Engine-WooCommerce-Sample-Products.csv",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing products before seeding",
        )
        parser.add_argument(
            "--download-images",
            action="store_true",
            help="Download product images from URLs",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        clear_existing = options["clear"]
        download_images = options["download_images"]

        if clear_existing:
            self.stdout.write("Clearing existing products...")
            Product.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS("Successfully cleared existing products")
            )

        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_path}"))
            return

        self.stdout.write(f"Reading CSV file: {csv_path}")

        try:
            with open(csv_path, "r", encoding="utf-8") as file:
                # Use csv.DictReader for easier column access
                reader = csv.DictReader(file)

                created_count = 0
                skipped_count = 0
                error_count = 0

                for row in reader:
                    try:
                        # Skip variations and only process simple and variable products
                        product_type = row.get("Type", "").strip().lower()
                        if product_type == "variation":
                            skipped_count += 1
                            continue

                        # Extract and clean data
                        product_data = self.extract_product_data(row, download_images)

                        if product_data:
                            # Check if product already exists (by name)
                            if not Product.objects.filter(
                                name=product_data["name"]
                            ).exists():
                                product = Product.objects.create(**product_data)
                                created_count += 1
                                self.stdout.write(f"Created: {product.name}")
                            else:
                                skipped_count += 1
                                self.stdout.write(
                                    f'Skipped (exists): {product_data["name"]}'
                                )
                        else:
                            skipped_count += 1

                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(f"Error processing row: {str(e)}")
                        )

                # Summary
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nSeeding completed!\n"
                        f"Created: {created_count} products\n"
                        f"Skipped: {skipped_count} products\n"
                        f"Errors: {error_count} products"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {str(e)}"))

    def extract_product_data(self, row, download_images=False):
        """Extract and map CSV data to Product model fields"""
        try:
            # Basic product information
            name = row.get("Name", "").strip()
            if not name:
                return None

            # Description - use short description if available, otherwise description
            short_desc = row.get("Short description", "").strip()
            long_desc = row.get("Description", "").strip()
            description = short_desc if short_desc else long_desc
            if not description:
                description = f"Quality product: {name}"

            # Price handling
            price = self.parse_decimal(row.get("Regular price", "0"), default=0.00)
            if price <= 0:
                # Try sale price if regular price is not available
                price = self.parse_decimal(row.get("Sale price", "0"), default=9.99)

            # Stock handling
            stock_value = row.get("Stock", "").strip()
            in_stock = row.get("In stock?", "").strip().lower()

            if stock_value and stock_value.isdigit():
                stock = int(stock_value)
            elif in_stock == "1" or in_stock == "true":
                stock = 100  # Default stock for items marked as in stock
            else:
                stock = 0

            # Category and tags
            category = self.clean_category(row.get("Categories", ""))
            tags = row.get("Tags", "").strip()

            # Featured status
            is_featured = row.get("Is featured?", "").strip() == "1"

            # Calculate discount if both regular and sale price exist
            regular_price = self.parse_decimal(row.get("Regular price", "0"))
            sale_price = self.parse_decimal(row.get("Sale price", "0"))
            discount = 0.00

            if regular_price > 0 and sale_price > 0 and sale_price < regular_price:
                discount = ((regular_price - sale_price) / regular_price) * 100
                price = sale_price  # Use sale price as the main price

            # Prepare product data
            product_data = {
                "name": name,
                "description": description,
                "price": price,
                "stock": stock,
                "category": category,
                "tags": tags,
                "average_rating": Decimal("0.00"),  # Default rating
                "discount": round(Decimal(str(discount)), 2),
                "is_featured": is_featured,
            }

            # Handle image download if requested
            if download_images:
                image_file = self.download_product_image(row.get("Images", ""), name)
                if image_file:
                    product_data["image"] = image_file

            return product_data

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Error extracting data for {name}: {str(e)}")
            )
            return None

    def parse_decimal(self, value, default=0.00):
        """Safely parse decimal values from CSV"""
        if not value or not isinstance(value, str):
            return Decimal(str(default))

        # Clean the value (remove currency symbols, etc.)
        cleaned = value.strip().replace("$", "").replace(",", "")

        try:
            return Decimal(cleaned)
        except (InvalidOperation, ValueError):
            return Decimal(str(default))

    def clean_category(self, category_string):
        """Clean and format category string"""
        if not category_string:
            return "General"

        # Split by comma and take the first category
        categories = category_string.split(",")
        if categories:
            # Clean up the category (remove > symbols and extra spaces)
            category = categories[0].strip().replace(">", "-").strip()
            return category if category else "General"

        return "General"

    def download_product_image(self, images_string, product_name):
        """Download the first product image from the images string"""
        if not images_string:
            return None

        # Split images by comma and get the first one
        image_urls = [url.strip() for url in images_string.split(",")]
        if not image_urls or not image_urls[0]:
            return None

        try:
            image_url = image_urls[0]
            self.stdout.write(f"Downloading image for {product_name}: {image_url}")

            response = requests.get(image_url, stream=True, timeout=30)
            response.raise_for_status()

            # Create a temporary file
            img_temp = NamedTemporaryFile(delete=True)
            img_temp.write(response.content)
            img_temp.flush()

            # Get file extension from URL
            file_extension = image_url.split(".")[-1].lower()
            if file_extension not in ["jpg", "jpeg", "png", "webp"]:
                file_extension = "jpg"

            # Create filename
            filename = f"{product_name.lower().replace(' ', '_')}.{file_extension}"

            return File(img_temp, name=filename)

        except requests.RequestException as e:
            self.stdout.write(
                self.style.WARNING(
                    f"Failed to download image for {product_name}: {str(e)}"
                )
            )
            return None
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(
                    f"Error processing image for {product_name}: {str(e)}"
                )
            )
            return None
