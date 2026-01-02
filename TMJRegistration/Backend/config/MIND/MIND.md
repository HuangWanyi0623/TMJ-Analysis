# MIND
MIND通常由一个距离 \( D_p \)、一个方差估计 \( V \) 和一个空间搜索区域 \( R \) 定义：
\[
\text{MIND}(I,x,\mathbf{r}) = \frac{1}{n}\exp\left(-\frac{D_p(I,x,x+\mathbf{r})}{V(I,x)}\right) \quad \mathbf{r} \in R \tag{4}
\]
where \( n \) is a normalisation constant (so that the maximum value is 1) and \( \mathbf{r} \in R \) defines the search region. By using MIND, an image will by represented by a vector of size \( |R| \) at each location \( x \).  

To evaluate Eq. (4) we need to define a distance measure between two voxels within the same image. As mentioned before, image patches offer attractive properties and are sensitive to the three main image features: points, gradients and uniformly textured regions. Therefore the straightforward choice of a distance measure \( D_p(x_1,x_2) \) between two voxels \( \mathbf{x}_1 \) and \( \mathbf{x}_2 \) is the sum of squared differences (SSD) of all voxels between the two patches \( P \) of size \( (2p+1)^d \) (with image dimension \( d \)) centred at \( \mathbf{x}_1 \) and \( \mathbf{x}_2 \).
\[ D_p(I,x_1,x_2) = \sum_{\mathbf{p} \in P} \left( I(x_1 + \mathbf{p}) - I(x_2 + \mathbf{p}) \right)^2 \tag{5} \]
We propose an alternative solution to calculate the exact patch-distance very efficiently using a convolution filter \( C \) of size \( (2p+1)^d \). First a copy of the image \( I' \) is translated by \( \mathbf{r} \) yielding \( I'(\mathbf{r}) \). Then the point-wise squared difference between \( I \) and \( I'(\mathbf{r}) \) is calculated. Finally, these intermediate values are convolved with the kernel \( C \), which effectively substitutes the SSD summation in Eq. (5):

\[ D_p(I,\mathbf{x},\mathbf{x} + \mathbf{r}) = C \star \left(I - I'(\mathbf{r})\right)^2 \tag{6} \]

This procedure is now repeated for all search positions \( \mathbf{r} \in R \). The solution of Eq. (6) is equivalent to the one obtained using Eq. (5). Using this method it is also easily possible to include a Gaussian weighting of the patches by using a Gaussian kernel \( C_\sigma \) of size \( (2p+1)^d \). The computational complexity per patch distance calculation is therefore reduced from \( (2p+1)^d \) to \( d(2p+1) \) for an arbitrary separable kernel and \( 3d \) for a uniform patch weighting. A similar procedure has been proposed in the context of windowed SSD aggregation by Scharstein and Szeliski (1996).  
 A better way of determining \( V(I,\mathbf{x}) \) is to use the mean of the patch distances themselves within a six-neighbourhood \( \mathbf{n} \in \mathcal{N} \):

\[ V(I,\mathbf{x}) = \frac{1}{6} \sum_{\mathbf{n} \in \mathcal{N}} D_p(I,\mathbf{x},\mathbf{x} + \mathbf{n}) \tag{8} \]

Using this approach (Eq. (8)), MIND can be automatically calculated without the need for any additional parameters.
One motivation for the use of MIND is that it allows to align multi-modal images using a simple similarity metric across modalities. Once the descriptors are extracted for both images, yielding a vector for each voxel, the similarity metric between two images is defined as the SSD between their corresponding descriptors. Therefore efficient optimisation algorithms, which converge rapidly can be used without further modification. In order to optimise the SSD of MIND, the similarity term \( \mathcal{S}(\mathbf{x}) \) of two images \( I \) and \( J \) at voxel \( \mathbf{x} \) can be to be defined as the sum of absolute differences between descriptors:

\[ \mathcal{S}(\mathbf{x}) = \frac{1}{|R|} \sum_{\mathbf{r} \in R} \left| \text{MIND}(I,\mathbf{x},\mathbf{r}) - \text{MIND}(J,\mathbf{x},\mathbf{r}) \right| \tag{9} \]

This requires \( |R| \) computations to evaluate the similarity at one voxel. Some algorithms, especially discrete optimisation techniques (Glocker et al., 2008, Shekhovtsov et al., 2008) use many cost function evaluations per voxel. In order to speed-up these computations the descriptor can be quantised to only 4 bit, without significant loss of accuracy. For \( |R|=6 \) all possible distances between descriptors can be pre-computed and stored in a lookup-table.


The similarity \( \mathcal{S} \) yields an intuitive display of the difference image after registration. 
Our new similarity metric based on the MIND can be used in any registration algorithm with little need for further modification.
# Gauss–Newton registration framework
This section describes the rigid registration framework, which will be used for all similarity metrics. We chose to use a Gauss–Newton optimisation scheme as it has an improved convergence compared to steepest descent methods (Zikic et al., 2010a). For single-modal registration using SSD as similarity metric, Gauss–Newton optimisation is equivalent to the well known Horn-Schunck optical flow solution (Horn and Schunck, 1981) as shown in Zikic et al. (2010b).
## Rigid registration
Rigid image registration aims to find the best transformation to align two images while constraining the deformation to be parameterised by a rigid-body (translation and rotation, 6 parameters). Extending this model to the more general affine transformation, the transformed location $\mathbf{x}'=(x',y',z')^T$ of a voxel $\mathbf{x}=(x,y,z)^T$ can be parameterised by $\mathbf{q}=(q_1,…,q_{12})$:

\[
\begin{aligned}
u &= x' - x = q_1 x + q_2 y + q_3 z + q_{10} - x \\
v &= y' - y = q_4 x + q_5 y + q_6 z + q_{11} - y \\
w &= z' - z = q_7 x + q_8 y + q_9 z + q_{12} - z
\end{aligned} \tag{10}
\]

where $\mathbf{u}=(u,v,w)^T$ is the displacement of $\mathbf{x}$. For a quadratic image similarity function $\mathbf{f}^2$, the Gauss–Newton method can be applied. It uses a linear approximation of the error term:

\[
\begin{aligned}
\mathbf{f}(\mathbf{x}') &\approx \mathbf{f}(\mathbf{x}) + \mathbf{J}(\mathbf{x}) \mathbf{u} \\
(\mathbf{J}^T \mathbf{J}) \mathbf{u}_{\text{gn}} &= -\mathbf{J}^T \mathbf{f}
\end{aligned} \tag{11}
\]

where $\mathbf{J}(\mathbf{x})$ is the derivative of the error term with respect to the transformation and $\mathbf{u}_{\text{gn}}$ is the update step. We insert Eq. (10) into Eq. (11) and differentiate with respect to $\mathbf{q}$ to calculate $\mathbf{J}(\mathbf{x})$. The advantage of this method is that we can directly use the point-wise cost function derivatives with respect to $\mathbf{u}$ to obtain an affine transformation, so that MIND has to be computed only once per image.  
The Gauss–Newton step is iteratively updated while transforming the source image towards the target. In order to speed up the convergence and avoid local minima, a multi-resolution scheme (with downsampling factors of 4 and 2) is used.