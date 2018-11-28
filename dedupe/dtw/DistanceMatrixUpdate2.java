import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.util.Scanner;

public class DistanceMatrixUpdate2 extends SqaureGridUpdate2
{
	static int[] ZeroCounter; //static members of the class which can be accessed anywhere
	static int[][] DistanceMatrix;
	static int[] LongestZeroString;
	static int[][] LZScoordinates;
	static int[] DataSetX;
  	static int[] DataSetY;



	public static void main(String[] args) throws FileNotFoundException 
	{

//QUICK TEST CASES
		// {1,1,2,2,1,1};//set of values that should have different LongestZeroString and ZeroCounter
		// {1,2,2,2,0,1};

	// int[] ArrayX = new int[]{1,1,2,3,2,1,0};//set of values that should have different LongestZeroString and ZeroCounter
	// int[] ArrayY = new int[]{0,1,1,2,3,2,1};

		//{0,0,0,1,1};//
		//{0,0,1,1,0};//


		// int[] ArrayX = new int[]{1,1,1,1,2,4,3,2}; //set of values that should have different LongestZeroString and ZeroCounter
		// int[] ArrayY = new int[]{1,1,1,2,4,4,3,2};

		//{2,2,2,3,3,2,2}; //set of values that should have different LongestZeroString and ZeroCounter
		//{2,2,2,2,3,2,2};

		 // int[] ArrayX = new int[]{3,2,3,1,3,1,2,1}; //GOOD example of finding starting coordinates of starting positions
		 // int[] ArrayY = new int[]{2,3,1,2,1,2,1,1};

		// int[] ArrayX = new int[]{80,82,85,85,94,90,90,75,77,80,81};
		// int[] ArrayY = new int[]{75,77,80,82,85,85,85,89,94,90,90};
		

		FileInputStream data = new FileInputStream("/Users/srapp/Desktop/data-analytics/dedupe/dtw/dataset.txt"); //X
        FileInputStream data2 = new FileInputStream("/Users/srapp/Desktop/data-analytics/dedupe/dtw/dataset2.txt"); //Y
        Scanner scanner = new Scanner(data);
        Scanner scanner2 = new Scanner(data2);

        DataSetX = new int[11044];//I looked at the number of lines in the file
        DataSetY = new int[11044];

        int i = 0;
        while(scanner.hasNextLine())
            {
                      
                DataSetX[i] = scanner.nextInt();
                DataSetY[i] = scanner2.nextInt();
               
                i++;
            } 
        scanner.close();
        scanner2.close();



		int HorizontalTraversals = DataSetX.length+DataSetY.length-1;
		ZeroCounter = new int[HorizontalTraversals]; //count zeros in each horizontal traversal each index is a travesal
		LongestZeroString = new int[HorizontalTraversals]; //tallys the longest continious string of zeros found in any given traversal
		LZScoordinates = new int[HorizontalTraversals][2];//records coordinates(in 2 column matrix) 0 index is X pos, 1 index is Y pos (seems reversed for some reason)


		if(DataSetX.length==DataSetY.length)
			{
				DistanceMatrix = new int[DataSetY.length][DataSetX.length]; //row then columns (incrementing the X values chances the column)
				//Columns of DisMatrixFillingHorizontally = DisMatrixCreater

				DisMatrixFillingHorizontally(DataSetY,DataSetX);
				//DisMatrixFillingHorizontally(ArrayY,ArrayX);//horizontally filling the Matrix, while counting zeros per traversal
			//	PrintMatrix(DistanceMatrix); //just a basic print function
			//	PrintMatrix(LZScoordinates);
				System.out.println("RESULT SECTION:");
				System.out.println("1. Array index of most zeros: " + getIndexOfLargest(ZeroCounter)); //index of most exact overlap(ala most matching values/zeros)
				System.out.println("2. Array index of longest string of zeros: " + getIndexOfLargest(LongestZeroString));
				System.out.println("3. Starting coordinates of the traversal(on the grid edge) with the longest continuous string of zeros: (x,y)_" + GridStartingCoordinates(LongestZeroString)); //index of most exact overlap(ala most matching values/zeros)
				System.out.println("4. Starting coordinates of the traversal(on the grid edge) with the most total zeros: (x,y)_" + GridStartingCoordinates(ZeroCounter));//converts the index of greatest traversal to the starting index(on the edge of the grid) of said traversal
				//DisMatrixCreater(ArrayY,ArrayX);//standard double for loop to create the proper distance matrix- to check agaisnt by horizontal creation
				
				System.out.println("5. Exact X & Y grid coordinates of longest String of Zeros (x,y)_"+ "(" + LZScoordinates[getIndexOfLargest(LongestZeroString)][1] + "," + LZScoordinates[getIndexOfLargest(LongestZeroString)][0] + ")");
				System.out.println("6. Percentage Match relative to perfect match_(most total zeros)_" + PercentMatch(ZeroCounter,DataSetX) + "%");
				System.out.println("7. Percentage Match relative to perfect match_(longest continous string of zeros)_"  + PercentMatch(LongestZeroString,DataSetX) + "%");

			}
		else
			{
				System.out.println("The Datasets being compared aren't the same length-");
			}
		
	}

//public static void ReadGoogleSlides()

	public static void DisMatrixFillingHorizontally(int[]D1, int[]D2)//int XstartPos, int YstartPos or maybe like a counter of # of traversals
	{//arguemnts are the vectors/arrays of data points, the X and Y starting position within the Matrix
		//Xpos = columns Ypos= rows

		int x = D1.length+D2.length-1;  //# of horizontal iterations needed to go through every potential unit of the grid. Its the number of edge points we use
										//13 is the answer for a 7 by 7 grid. 
										//its equal to the number of edge values or length + width - 1	
		int XstartPos = 0;
		int YstartPos = 0;
		int traversalsFromMiddle = 0;
		int ZeroCounter = 0; //index of ZeroCounter array- it is the same as the traversalFromMiddle untill TFM is reset after half the grid is filled
		//with evenly sized arrays the X value will always be Odd so we have to account for java rounding down by adding 1
			
		for(int i=0; i<((x/2)+1); i++)//goes through as many times are you need to traverse the middle traversal to the bottom left corner.
			{
				traversalsFromMiddle = MatrixHelper(D1, D2, XstartPos, YstartPos, traversalsFromMiddle, ZeroCounter)+1; //if the Helper returns the traversal count we can use its value even if the method is creating seperate variables
				ZeroCounter++;
				XstartPos = traversalsFromMiddle;
			}

			traversalsFromMiddle=1;
			XstartPos = 0;//give new starting edge index values
			YstartPos = 1;
			
			for(int p=0; p<(x/2); p++) //traversals from 1 above the middle to top right corner.
				{
					traversalsFromMiddle = MatrixHelper(D1, D2, XstartPos, YstartPos, traversalsFromMiddle, ZeroCounter)+1; 
					ZeroCounter++;
					YstartPos = traversalsFromMiddle;
				}
	}


			/*to know when to make the recursive call A know how many grid positions must be filled before hand and count or B know the final position index you will land at

			if the length/width of the DisMX grid are equal(THE GRID IS A SQUARE) the length of the longest horizontal(corner to corner) requires sidelength amount of sqaure traversals.
			The longest traversal of a grid with sidelength of X is X operations. Starting at position (0,0)
			starting position (0,y) or (y,0) (where sidelength>y>0) takes Sidelength-Y operations to reach its final grid position

			ex with #s: a  7 by 7 grid's longest traversal is 7 operations long(Starting at position 0,0)
			(0,1)=6op (0,2) = 5...(0,6) = 1 same with (1,0)=6op, (2,0)=5op....(6,0)=1op
			longest traversal(starting at 0,0) is maximum the length of the shorter side 
			


			for a sqaure the longest traversal ends at (sidelength, sidelength) (the perfect diagonal)
			starting position (y,0) ends at position (sidelength-1, sidelength-y-1) //moving towards bottom right corner of grid
			starting position (0,x) ends at position (sidelength-x-1, sidelength-1) //moving towards top right corner of grid
			//we do -1 because the side length starts at 1 but the indexing of the grid starts at 0. so we have to adjust
			*/



	public static int MatrixHelper(int[]D1, int[]D2, int Xpos, int Ypos, int traversals, int ZerocIndex)
	{//the matrix helper function does one complete horizontal traversal of the grid

		int SidelengthX = D1.length; //.length is the actually amount of positions allocated in memory so index 0-9 is length 10
		boolean test = true;
		int ActiveZeroCounter = 0;

		while(test==true)
				{
				//System.out.println("(Y,X)" + Ypos + "," + Xpos);
				//System.out.println("traversals = " + traversals); //doesn't work in secound half of the listing unless the traversal values are reset to 1

				int DistanceValue = (D2[Ypos]-D1[Xpos])*(D2[Ypos]-D1[Xpos]); //the difference between the values squared
				DistanceMatrix[Xpos][Ypos] = DistanceValue;//put value into Matrix

				if(DistanceValue == 0)//found match (maybe pick a larger range ala 2-6 to allow for puedomatch)
					{
				       	ZeroCounter[ZerocIndex] = ZeroCounter[ZerocIndex]+1;//increment index of total zeros in diagonal traversal
				 		ActiveZeroCounter = ActiveZeroCounter+1;
						//System.out.println("Active Zero Counter: " + ActiveZeroCounter);
					}
				else //found non zero value
					{
						if(ActiveZeroCounter > LongestZeroString[ZerocIndex])//if the String of zeros currently found is greater than what we have previously found for this traversal
						{
							LongestZeroString[ZerocIndex] = ActiveZeroCounter;//change the value of longest Active Zero counter to the active zero counter
							//System.out.println("#: " + (Xpos - ActiveZeroCounter) + "," + (Ypos - ActiveZeroCounter));
							LZScoordinates[ZerocIndex][0] = (Xpos - ActiveZeroCounter +1); 
							LZScoordinates[ZerocIndex][1] = (Ypos - ActiveZeroCounter +1); 

						}
						//System.out.println(ActiveZeroCounter);
						ActiveZeroCounter = 0; //reset the active counter to zero 
					}

				//leave loop if the array indexs being called match the final position the call reaches
				if(Xpos == SidelengthX-1-traversals && Ypos == SidelengthX-1)//-1 is because array index starts at zero side length doesn't.
					{
					//System.out.println("time to break-TR");
					//System.out.println("number of zeros:" + ZeroCounter[ZerocIndex]);
						if(ActiveZeroCounter > LongestZeroString[ZerocIndex])//Need to check in senario when the traversal ends in a match/zero
							{
								LongestZeroString[ZerocIndex] = ActiveZeroCounter;
						//		System.out.println("#: " + (Xpos - ActiveZeroCounter + 1) + "," + (Ypos - ActiveZeroCounter + 1));
								LZScoordinates[ZerocIndex][0] = (Xpos - ActiveZeroCounter + 1); 
								LZScoordinates[ZerocIndex][1] = (Ypos - ActiveZeroCounter + 1); 
						
							}

						test = false;
						break;
					}

				if(Xpos== SidelengthX-1 && Ypos== SidelengthX-1-traversals)//the ending coordinates for values below the middle traversal towards to bottom left
					{
					//System.out.println("time to break2-BL");
					//System.out.println("number of zeros:" + ZeroCounter[ZerocIndex]);
						if(ActiveZeroCounter > LongestZeroString[ZerocIndex])//Need to check in senario when the traversal ends in a match/zero
							{
								LongestZeroString[ZerocIndex] = ActiveZeroCounter;//change the value of longest Active Zero counter to the active zero counter
							//System.out.println("#: " + (Xpos - ActiveZeroCounter + 1) + "," + (Ypos - ActiveZeroCounter + 1));
								LZScoordinates[ZerocIndex][0] = (Xpos - ActiveZeroCounter + 1); 
								LZScoordinates[ZerocIndex][1] = (Ypos - ActiveZeroCounter + 1); 
							}

						test = false;
						break;
					}

				Xpos = Xpos+1;
				Ypos = Ypos+1;
				}

		return traversals;		//so we can keep track of the position of the traversal
		//we need to know which travesal we have just done. To know where to start the next one
	}


	public static String GridStartingCoordinates(int[] array) //Gets starting coordinates of traversal based on largest value in array
	{
		int LargestValueIndex = getIndexOfLargest(array);
		String coordinates;

		if(LargestValueIndex>((array.length/2)))
			{
				coordinates = new String(("(" + (LargestValueIndex-((array.length/2))) + "," + 0 +") "+ "value: " + array[LargestValueIndex]));
				//if the starting value was in the top half of the grid
				//this is because the grid is made middle to bottom left corner then back to the middle line to top right corner
			}
		else
			{
				coordinates = new String("(" + 0 + "," + LargestValueIndex + ") " + "value: " + array[LargestValueIndex]);
			} 

		return coordinates;
	}

	public static double PercentMatch(int[]Array, int[]GridSideLength)
	{ 	//takes in two arrays. Finds the percent match between largest value in first array and max length in second array
		int IndexOfLargest = getIndexOfLargest(Array);
		double ValueTotal = GridSideLength.length;
		double ValueMatchs = (double) Array[IndexOfLargest];
		double PercentMatch = (ValueMatchs/ValueTotal)*100;
		return PercentMatch;
	}
	
}

