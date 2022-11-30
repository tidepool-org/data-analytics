#include <stdio.h>
#include <stdlib.h>
#include <fftw3.h>
#include <math.h>



double * multiply(double * x, int n , double * y , int m , double * z);
double * zNorm(double * x, int n, double * y);
double * findNN(double * x, double * y, int n, int m, double * dist);



int main(int argc, char* argv[])
{
	//Assume n > m

	int n = atol(argv[3]); 
	int m = atol(argv[4]);
	double *x, *y, *dist;

	//Memory Allocation
	
	FILE * fp ; errno_t err = fopen_s(&fp,argv[1],"r");
	  if( err )
      printf_s( "The file fscanf.out was not opened\n" );
	FILE * fp1 ; err = fopen_s(&fp1,argv[2],"r");
		   if( err )
      printf_s( "The file fscanf.out was not opened\n");

	x = (double *)malloc(sizeof(double) * n);
	y = (double *)malloc(sizeof(double) * m);
	dist = (double *)malloc(sizeof(double) * n);

	//Data Input
	for ( int i = 0 ; i < n ; i ++ )
	{
		double d;
		fscanf_s(fp,"%lf",&d);
		x[i] = d;
		if( i < m )
		{
			fscanf_s(fp1,"%lf",&d);
			y[i] = d;
		}
	}

	dist = findNN(x,y,n,m,dist);
	
	double minm = 99999999999999.000222;
	int mini = 0;
	for ( int i = 0 ; i < n-m+1	 ; i++ )
		if( dist[i] < minm )
		{	minm = dist[i]; mini = i; }
	
	printf("Nearest Neighbor Distance is %lf\nNearest Neighbor location is %d (starting at 1)\n",minm, mini);
	fclose(fp); fclose(fp1);
    



	free(x); free(y); free(dist);

	system("PAUSE");
}


double * findNN(double * x, double * y, int n, int m, double * dist)
{
	
	//Assume n > m
	double *z ;
	double *cx, *cx2, *cy, *cy2;

	//Allocation
	cx = (double *)malloc(sizeof(double) * (n+1));
	cx2 = (double *)malloc(sizeof(double) * (n+1));
	cy = (double *)malloc(sizeof(double) * (m+1));
	cy2 = (double *)malloc(sizeof(double) * (m+1));

	//Normalize
	x = zNorm(x,n,x);
	y = zNorm(y,m,y);

	//Compute the cumulative sums
	cx[0] = cx2[0] = cy[0] = cy2[0] = 0.0;
	for( int i = 1 ; i <= n; i++ )
	{
		cx[i] = cx[i-1]+x[i-1];
		cx2[i] = cx2[i-1]+x[i-1]*x[i-1];
		if( i <= m )
		{
			cy[i] = cy[i-1]+y[i-1];
			cy2[i] = cy2[i-1]+y[i-1]*y[i-1];

		}

	}

	//Compute the multiplication numbers
	z = (double *)malloc(sizeof(double)*2*n);
	z = multiply(x,n,y,m,z);
	
	//y Stats
				
	double sumy = cy[m];
	double sumy2 = cy2[m];
	double meany = sumy/m;
	double sigmay = (sumy2/m)-meany*meany;
	sigmay = sqrt(sigmay);
			

	//The Search
	for( int j = 0 ; j < n-m+1 ; j=j+1 )
	{
				double sumxy = z[m-1+j];

				double sumx = cx[j+m]-cx[j];
				double sumx2 = cx2[j+m]-cx2[j];
				double meanx = sumx/m;
				double sigmax = (sumx2/m)-meanx*meanx;
				sigmax = sqrt(sigmax);

				double c = ( sumxy - m*meanx*meany ) / ( m*sigmax*sigmay );
				dist[j] = sqrt(2*m*(1-c));
				
	}
	
    free(cx); free(cx2); free(cy); free(cy2);
	free(z);
	return dist;
}


double * zNorm(double * x, int n, double * y)
{
	double ex = 0, ex2 = 0;
	for(int i = 0 ; i < n ; i++ )
	{
		ex += x[i];
		ex2 += x[i]*x[i];
	}
	double	mean = ex/n;
    double std = ex2/n;
    std = sqrt(std-mean*mean);
	for(int i = 0 ; i < n ; i++ )
		y[i] = (x[i]-mean)/std;
	return y;
}

double * multiply(double * x, int n , double * y , int m , double * z)
{
	fftw_complex * X, * Y, * Z , *XX, *YY, *ZZ;
    fftw_plan p;
    
	//assuming n > m
	X = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * 2 * n);
	Y = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * 2 * n);
	XX = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * 2 * n);
	YY = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * 2 * n);
	Z = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * 2 * n);
	ZZ = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * 2 * n);


	for(int i = 0 ; i < 2*n ; i++ )
	{
		X[i][1] = 0; Y[i][1] = 0; //iaginary part is always zero
		if(i < n )
			X[i][0] = x[i];
		else
			X[i][0] = 0;

		if(i < m )
			Y[i][0] = y[m-i-1]; //reversing y
		else
			Y[i][0] = 0;
	}


    p = fftw_plan_dft_1d(2 * n, X, XX, FFTW_FORWARD, FFTW_ESTIMATE);
    fftw_execute(p); 
    
    p = fftw_plan_dft_1d(2 * n, Y, YY, FFTW_FORWARD, FFTW_ESTIMATE);
    fftw_execute(p); 

	for(int i = 0 ; i < 2*n; i++)
	{
		ZZ[i][0] = XX[i][0]*YY[i][0] - XX[i][1]*YY[i][1]; 
		ZZ[i][1] = XX[i][1]*YY[i][0] + XX[i][0]*YY[i][1];
	}
	
	p = fftw_plan_dft_1d(2 * n, ZZ , Z , FFTW_BACKWARD, FFTW_ESTIMATE);
    fftw_execute(p); 


	for(int i = 0; i < 2*n; i++ )
		z[i] = Z[i][0]/(2*n);
	
	fftw_destroy_plan(p);
    fftw_free(X); fftw_free(Y);
	fftw_free(XX); fftw_free(YY);
	fftw_free(Z); fftw_free(ZZ);
	
	return z;
}