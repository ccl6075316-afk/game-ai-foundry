// Metadata/signature/field-offset recovery only. Empty bodies below are placeholders, NOT recovered algorithms.
// Source APK 8a6f23099eb334f2d4a7a7a02058c1cf021551dd7e892cbf426c4c511b5ac7b7; IL2CPP metadata v31.
// Namespace: FishFlock
public struct CollisionArea // TypeDefIndex: 2032
{
	// Fields
	public Vector3 position; // 0x0
	public Vector3 size; // 0xC
	public int type; // 0x18
}

// Namespace: FishFlock
public enum FishMovementAxis // TypeDefIndex: 2033
{
	// Fields
	public int value__; // 0x0
	public const FishMovementAxis XYZ = 0;
	public const FishMovementAxis XY = 1;
	public const FishMovementAxis XZ = 2;
}

// Namespace: FishFlock
public struct FishData // TypeDefIndex: 2034
{
	// Fields
	public Vector3 position; // 0x0
	public Vector3 velocity; // 0xC
	public float speed; // 0x18
	public float rot_speed; // 0x1C
	public float speed_offset; // 0x20
	public float scale; // 0x24
	public bool isControlledByGroup; // 0x28
	public Transform transform; // 0x30

	// Properties
	public Vector3 rotFwd { get; }

	// Methods

	// RVA: 0x207AB6C Offset: 0x2076B6C VA: 0x207AB6C
	public Vector3 get_rotFwd() { }
}

// Namespace: FishFlock
[SaveDuringPlay]
public class FishGroup : MonoBehaviour // TypeDefIndex: 2035
{
	// Fields
	private FishMovementAxis FishMovementAxis; // 0x20
	public bool debugDraw; // 0x24
	public bool isControllByController; // 0x25
	public bool isInsideBox; // 0x26
	[MinMax(0, 10)]
	public Vector2 speed; // 0x28
	[MinMax(0, 10)]
	public Vector2 rotation; // 0x30
	public int priority; // 0x38
	public float spawnRadius; // 0x3C
	public float fleeRadius; // 0x40
	public float neighbourDistance; // 0x44
	[HideInInspector]
	public float _neighbourDistance; // 0x48
	private float intendedNeighbourDistance; // 0x4C
	private float neighbourDistanceRateSmoothRate; // 0x50
	public bool followTarget; // 0x54
	public Transform target; // 0x58
	[HideInInspector]
	public List<FishData> fishesData; // 0x60
	public bool recalculatePoints; // 0x68
	public float groupAreaSpeed; // 0x6C
	public List<Transform> followTargets; // 0x70
	public Vector3[] targetPositions; // 0x78
	public bool isIndexLoop; // 0x80
	[HideInInspector]
	public List<Vector3> prePositions; // 0x88
	public int currentTargetPosIndex; // 0x90
	[HideInInspector]
	public Vector3 groupAnchor; // 0x94
	[MinMax(1, 5)]
	public Vector2Int targetPointsAmount; // 0xA0
	private FishFlockController controller; // 0xA8

	// Methods

	// RVA: 0x207AB94 Offset: 0x2076B94 VA: 0x207AB94
	public void Init(FishFlockController controller) { }

	// RVA: 0x207AEBC Offset: 0x2076EBC VA: 0x207AEBC
	public void UpdateGroupAnchor() { }

	// RVA: 0x207AC48 Offset: 0x2076C48 VA: 0x207AC48
	public void GeneratePath(bool isResetIndex = True) { }

	// RVA: 0x207B448 Offset: 0x2077448 VA: 0x207B448
	public void SetGroupPosition(Vector3 at) { }

	// RVA: 0x207B2D8 Offset: 0x20772D8 VA: 0x207B2D8
	public Vector3 RandomPos() { }

	// RVA: 0x207B5C0 Offset: 0x20775C0 VA: 0x207B5C0
	public void OnDrawGizmos() { }

	// RVA: 0x207B9AC Offset: 0x20779AC VA: 0x207B9AC
	public void OnUpdate() { }

	// RVA: 0x207BC9C Offset: 0x2077C9C VA: 0x207BC9C
	private FishData CreateBehaviour(float scale) { }

	// RVA: 0x207BE38 Offset: 0x2077E38 VA: 0x207BE38
	public FishData AddFish(GameObject fishPrefab, float scale) { }

	// RVA: 0x207BF5C Offset: 0x2077F5C VA: 0x207BF5C
	public FishData AddFish(Transform fishTransform, float scale) { }

	// RVA: 0x207C2FC Offset: 0x20782FC VA: 0x207C2FC
	private void OnValidate() { }

	// RVA: 0x207C300 Offset: 0x2078300 VA: 0x207C300
	public void ResetSpeed() { }

	// RVA: 0x207C454 Offset: 0x2078454 VA: 0x207C454
	public void SetScale(Transform fishTransform, float scale) { }

	// RVA: 0x207C548 Offset: 0x2078548 VA: 0x207C548
	public void SetScale(int index, float scale) { }

	// RVA: 0x207C630 Offset: 0x2078630 VA: 0x207C630
	public bool RemoveFish(int index = 0) { }

	// RVA: 0x207C730 Offset: 0x2078730 VA: 0x207C730
	public bool RemoveFish(Transform fishTransform) { }

	// RVA: 0x207C480 Offset: 0x2078480 VA: 0x207C480
	public int FindFishIndexByTransform(Transform fishTransform) { }

	// RVA: 0x207C74C Offset: 0x207874C VA: 0x207C74C
	public int GetFishCount() { }

	// RVA: 0x207C794 Offset: 0x2078794 VA: 0x207C794
	public void AddPrePosition(Vector3 pos) { }

	// RVA: 0x207B7CC Offset: 0x20777CC VA: 0x207B7CC
	public Vector3 CalculateCenterPoint() { }

	// RVA: 0x207C868 Offset: 0x2078868 VA: 0x207C868
	public void UpdateFishDataByTransform(FishData fishData) { }

	// RVA: 0x207C97C Offset: 0x207897C VA: 0x207C97C
	public int GetFishDataIndexByTransform(Transform fishTransform) { }

	// RVA: 0x207CA38 Offset: 0x2078A38 VA: 0x207CA38
	public void .ctor() { }
}

// Namespace: FishFlock
[RequireComponent(typeof(FishGroup))]
[SaveDuringPlay]
public class FishGroupController : MonoBehaviour // TypeDefIndex: 2036
{
	// Fields
	public GameObject fishPrefab; // 0x20
	public int initNum; // 0x28
	public string animState; // 0x30
	[MinMax(0, 2)]
	public Vector2 scale; // 0x38
	private FishGroup fishGroup; // 0x40
	private FishFlockController controller; // 0x48
	private Vector2 _lastScale; // 0x50

	// Methods

	// RVA: 0x207CBC0 Offset: 0x2078BC0 VA: 0x207CBC0
	private void Start() { }

	// RVA: 0x207CDB0 Offset: 0x2078DB0 VA: 0x207CDB0
	private void ResetFish() { }

	// RVA: 0x207D094 Offset: 0x2079094 VA: 0x207D094
	private void OnValidate() { }

	// RVA: 0x207D098 Offset: 0x2079098 VA: 0x207D098
	public void .ctor() { }
}

// Namespace: FishFlock
[CreateAssetMenu(fileName = "New FlockGfxProfile", menuName = "Fish Flock/Create Flock Gfx Profile")]
public class FlockGfxProfile : ScriptableObject // TypeDefIndex: 2037
{
	// Fields
	[Tooltip("The prefab that will be instantiated to manipulate the fishes. If you are using instancing this is not going to be used.")]
	public GameObject prefab; // 0x18
	[Tooltip("Mesh to be drawn when using instancing.")]
	public Mesh mesh; // 0x20
	[Tooltip("Instanced Material to be used to draw the fishes.")]
	public Material material; // 0x28
	public ShadowCastingMode shadowCasting; // 0x30
	public bool receiveShadows; // 0x34

	// Methods

	// RVA: 0x207D138 Offset: 0x2079138 VA: 0x207D138
	public void .ctor() { }
}

// Namespace: FishFlock
public struct PredatorData // TypeDefIndex: 2038
{
	// Fields
	public Vector3 position; // 0x0
	public float radius; // 0xC
}

// Namespace: FishFlock
public enum FlockRenderingMode // TypeDefIndex: 2039
{
	// Fields
	public int value__; // 0x0
	public const FlockRenderingMode GAMEOBJECT = 0;
	public const FlockRenderingMode INSTANCING = 1;
}

// Namespace: FishFlock
public enum FlockComputationMode // TypeDefIndex: 2040
{
	// Fields
	public int value__; // 0x0
	public const FlockComputationMode CPU = 0;
	public const FlockComputationMode CPU_AND_ONE_THREAD = 1;
	public const FlockComputationMode GPU = 2;
}

// Namespace: FishFlock
[SaveDuringPlay]
public class FishFlockController : MonoBehaviour // TypeDefIndex: 2041
{
	// Fields
	public float swimmingAreaWidth; // 0x20
	public float swimmingAreaHeight; // 0x24
	public float swimmingAreaDepth; // 0x28
	public bool debugDraw; // 0x2C
	public FishMovementAxis FishMovementAxis; // 0x30
	public FlockComputationMode computationMode; // 0x34
	[MinMax(0, 10)]
	public Vector2 rotation; // 0x38
	private float _neighbourDistance; // 0x40
	public int lookAheadSteps; // 0x44
	public float force; // 0x48
	public float colliderSizeOffset; // 0x4C
	public Collider[] colliders; // 0x50
	public bool updateAtRuntime; // 0x58
	private CollisionArea[] collisionData; // 0x60
	private int collisionDataLength; // 0x68
	private SimpleCounter refreshCollisionCounter; // 0x70
	private float unityDeltaTime; // 0x78
	private ThreadProcess threadProcess; // 0x80
	public List<FishGroup> fishGroups; // 0x88
	private List<int> highPriorityIndexList; // 0x90
	private Vector3 volumeSize; // 0x98

	// Methods

	// RVA: 0x207D14C Offset: 0x207914C VA: 0x207D14C
	private void Awake() { }

	// RVA: 0x207CCC0 Offset: 0x2078CC0 VA: 0x207CCC0
	public void AddFishGroup(FishGroup fishGroup) { }

	// RVA: 0x207D84C Offset: 0x207984C VA: 0x207D84C
	public void RemoveFishGroup(FishGroup fishGroup) { }

	// RVA: 0x207D8A4 Offset: 0x20798A4 VA: 0x207D8A4
	public void AddCollider(Collider collider) { }

	// RVA: 0x207DAD8 Offset: 0x2079AD8 VA: 0x207DAD8
	public void RemoveCollider(Collider collider) { }

	// RVA: 0x207D2A0 Offset: 0x20792A0 VA: 0x207D2A0
	private void InitializeFishes() { }

	// RVA: 0x207D33C Offset: 0x207933C VA: 0x207D33C
	private void UpdateCollisionData() { }

	// RVA: 0x207D7B8 Offset: 0x20797B8 VA: 0x207D7B8
	private void CreateCollisionData() { }

	// RVA: 0x207DE90 Offset: 0x2079E90 VA: 0x207DE90
	private Vector3 Flee(FishData data, Vector3 positionToEvade) { }

	// RVA: 0x207DFA8 Offset: 0x2079FA8 VA: 0x207DFA8
	private void ComputeFlockBehaviours() { }

	// RVA: 0x207EE4C Offset: 0x207AE4C VA: 0x207EE4C
	private void Update() { }

	// RVA: 0x207EF60 Offset: 0x207AF60 VA: 0x207EF60
	private void OnDestroy() { }

	// RVA: 0x207EF70 Offset: 0x207AF70 VA: 0x207EF70
	private void ClearAll() { }

	// RVA: 0x207F0C4 Offset: 0x207B0C4 VA: 0x207F0C4
	private void OnDrawGizmos() { }

	// RVA: 0x207EE1C Offset: 0x207AE1C VA: 0x207EE1C
	private Vector3 GetSeparationVector(Vector3 diff, float len, float neighbourDistance) { }

	// RVA: 0x207EE00 Offset: 0x207AE00 VA: 0x207EE00
	private float VecMag(Vector3 v) { }

	// RVA: 0x207F13C Offset: 0x207B13C VA: 0x207F13C
	public void .ctor() { }
}

// Namespace: FishFlock
public class FlockPredator : MonoBehaviour // TypeDefIndex: 2042
{
	// Fields
	public float fleeRadius; // 0x20
	public bool drawGizmos; // 0x24
	private Vector3 m_position; // 0x28

	// Properties
	public Vector3 Position { get; }

	// Methods

	// RVA: 0x207F23C Offset: 0x207B23C VA: 0x207F23C
	public Vector3 get_Position() { }

	// RVA: 0x207F248 Offset: 0x207B248 VA: 0x207F248
	private void Update() { }

	// RVA: 0x207F278 Offset: 0x207B278 VA: 0x207F278
	private void OnDrawGizmos() { }

	// RVA: 0x207F2C8 Offset: 0x207B2C8 VA: 0x207F2C8
	public void .ctor() { }
}

// Namespace: FishFlock
public class ThreadManager : MonoBehaviour // TypeDefIndex: 2043
{
	// Fields
	private static GameObject instance; // 0x0
	private static ThreadManager singleton; // 0x8
	private readonly List<ThreadProcess> processes; // 0x20

	// Methods

	// RVA: 0x207F334 Offset: 0x207B334 VA: 0x207F334
	private static void SetupSingleton() { }

	// RVA: 0x207F4C4 Offset: 0x207B4C4 VA: 0x207F4C4
	private void Start() { }

	// RVA: 0x207F568 Offset: 0x207B568 VA: 0x207F568
	private void Update() { }

	// RVA: 0x207F6AC Offset: 0x207B6AC VA: 0x207F6AC
	private void OnDestroy() { }

	// RVA: 0x207F8EC Offset: 0x207B8EC VA: 0x207F8EC
	private void OnApplicationQuit() { }

	// RVA: 0x207F8F0 Offset: 0x207B8F0 VA: 0x207F8F0
	private void OnSceneIsUnloaded(Scene arg0) { }

	// RVA: 0x207F6B0 Offset: 0x207B6B0 VA: 0x207F6B0
	private void Reset() { }

	// RVA: 0x207DCD4 Offset: 0x2079CD4 VA: 0x207DCD4
	public static ThreadProcess DoTask(Action callback) { }

	// RVA: 0x207EF80 Offset: 0x207AF80 VA: 0x207EF80
	public static void EndTask(ThreadProcess process) { }

	// RVA: 0x207F9EC Offset: 0x207B9EC VA: 0x207F9EC
	public void .ctor() { }
}

// Namespace: FishFlock
public class ThreadProcess // TypeDefIndex: 2044
{
	// Fields
	private bool running; // 0x10
	private Action callback; // 0x18
	[CompilerGenerated]
	private AutoResetEvent <AutoEvt>k__BackingField; // 0x20

	// Properties
	public AutoResetEvent AutoEvt { get; set; }

	// Methods

	[CompilerGenerated]
	// RVA: 0x207FA74 Offset: 0x207BA74 VA: 0x207FA74
	public AutoResetEvent get_AutoEvt() { }

	[CompilerGenerated]
	// RVA: 0x207FA7C Offset: 0x207BA7C VA: 0x207FA7C
	private void set_AutoEvt(AutoResetEvent value) { }

	// RVA: 0x207F8FC Offset: 0x207B8FC VA: 0x207F8FC
	internal void .ctor(Action _callback) { }

	// RVA: 0x207FA84 Offset: 0x207BA84 VA: 0x207FA84
	private void DoRun() { }

	// RVA: 0x207F8F4 Offset: 0x207B8F4 VA: 0x207F8F4
	public void Stop() { }

	[CompilerGenerated]
	// RVA: 0x207FAD8 Offset: 0x207BAD8 VA: 0x207FAD8
	private void <.ctor>b__6_0(object p) { }
}

// Namespace: FishFlock
public class VecHelpers // TypeDefIndex: 2045
{
	// Methods

	// RVA: 0x207FADC Offset: 0x207BADC VA: 0x207FADC
	public static Vector3 mul(Vector3 l, Vector3 r) { }

	// RVA: 0x207FAEC Offset: 0x207BAEC VA: 0x207FAEC
	public static Vector3 mul(Vector3 l, float r) { }

	// RVA: 0x207FAFC Offset: 0x207BAFC VA: 0x207FAFC
	public void .ctor() { }
}

// Namespace: FishFlock.Utils
public class MinMaxAttribute : PropertyAttribute // TypeDefIndex: 2046
{
	// Fields
	public float Min; // 0x10
	public float Max; // 0x14

	// Methods

	// RVA: 0x207FB04 Offset: 0x207BB04 VA: 0x207FB04
	public void .ctor(float min, float max) { }
}
