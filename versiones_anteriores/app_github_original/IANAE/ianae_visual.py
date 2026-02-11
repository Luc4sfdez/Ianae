"""Módulo de extensión visual para IANAE"""

import numpy as np
import torch
from torchvision.models import resnet50, vit_b_16, efficientnet_b0
from PIL import Image
from enum import Enum

class ModeloVisual(Enum):
    RESNET50 = "resnet50"
    VIT = "vit"
    EFFICIENTNET = "efficientnet"

class IANAEVisual:
    def __init__(self, dim_vector_semantico=100, modelo=ModeloVisual.RESNET50):
        self.dim_vector_semantico = dim_vector_semantico
        self.modelo = modelo
        self.modelo_visual = self._cargar_modelo_visual()
        self._configurar_dimensiones()
        
    def _cargar_modelo_visual(self):
        """Carga modelo de visión según selección"""
        if self.modelo == ModeloVisual.VIT:
            modelo = vit_b_16(pretrained=True)
            modelo = torch.nn.Sequential(*(list(modelo.children())[:-1]))
        elif self.modelo == ModeloVisual.EFFICIENTNET:
            modelo = efficientnet_b0(pretrained=True)
            modelo = torch.nn.Sequential(*(list(modelo.children())[:-1]))
        else:  # RESNET50 por defecto
            modelo = resnet50(pretrained=True)
            modelo = torch.nn.Sequential(*(list(modelo.children())[:-1]))
            
        modelo.eval()
        return modelo
        
    def _configurar_dimensiones(self):
        """Configura dimensiones según modelo seleccionado"""
        if self.modelo == ModeloVisual.VIT:
            self.dim_vector_visual = 768
        elif self.modelo == ModeloVisual.EFFICIENTNET:
            self.dim_vector_visual = 1280
        else:  # RESNET50
            self.dim_vector_visual = 2048

    def extraer_caracteristicas(self, imagen, batch=False):
        """Extrae vector de características de una imagen o lote de imágenes"""
        if isinstance(imagen, str):
            imagen = Image.open(imagen)
            if imagen.mode != 'RGB':
                imagen = imagen.convert('RGB')
            imagenes = [imagen]
        elif isinstance(imagen, list):
            imagenes = []
            for img in imagen:
                if isinstance(img, str):
                    img = Image.open(img)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                imagenes.append(img)
        
        # Configurar transformaciones según modelo
        if self.modelo == ModeloVisual.VIT:
            size = 224
            mean = [0.5, 0.5, 0.5]
            std = [0.5, 0.5, 0.5]
        else:
            size = 256
            mean = [0.485, 0.456, 0.406]
            std = [0.229, 0.224, 0.225]
            
        transform = transforms.Compose([
            transforms.Resize(size),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std)
        ])
        
        # Procesar imágenes
        tensores = torch.stack([transform(img) for img in imagenes])
        
        with torch.no_grad():
            caracteristicas = self.modelo_visual(tensores)
        
        if batch:
            return caracteristicas.squeeze().numpy()
        return caracteristicas.squeeze()[0].numpy() if len(imagenes) == 1 else caracteristicas.squeeze().numpy()

    def crear_concepto_visual(self, nombre, imagen=None, vector_visual=None):
        """Crea un nuevo concepto con componente visual"""
        if imagen is not None:
            vector_visual = self.extraer_caracteristicas(imagen)
        elif vector_visual is None:
            vector_visual = np.random.normal(0, 1, self.dim_vector_visual)
            
        vector_visual = vector_visual / np.linalg.norm(vector_visual)
        
        return {
            'nombre': nombre,
            'vector_visual': vector_visual,
            'activaciones': 0
        }
